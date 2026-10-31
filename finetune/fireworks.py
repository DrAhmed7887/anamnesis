"""Fireworks AI REST client for the Muse Glimmer 30B LoRA fine-tune (plan: evidence/finetune/plan.md).

Standard library only and REST only (no firectl, no SDK). Every subcommand prints the exact requests it would
send and sends nothing, unless --live is given.

    upload <name> <file.jsonl>                    create a dataset, upload the file, wait for READY
    train <dataset> <eval-dataset> <output-model> LoRA SFT, rank 16, 2 epochs
    status <job>                                  state, progress, last lines of the metrics file
    shapes [model] [--addons]                     validated deployment shapes (read-only, free)
    deploy <model> [--alone] [--shape NAME]       on-demand deployment (bills per GPU-hour)
    undeploy <deployment> [--force]               delete it
    chat <model> <messages.json>                  one chat-completions call

Safety, all enforced in code:
- the key is read from the Keychain at run time, sent only to api.fireworks.ai, never follows a redirect
  and is masked in every message printed (read_key, check_call, http, scrub);
- dry run by default; --live sends;
- train, deploy and chat run scripts/spend_check.py first and stop if it fails (Runner.spend_gate);
- a fine-tuning job without loraRank is refused: through REST an omitted rank means full-parameter training;
- a model id containing -contributor is refused, as the repo's providers do.
"""

import argparse
import json
import re
import secrets
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "<account>"
HOST = "api.fireworks.ai"
BASE_MODEL = "accounts/fireworks/models/muse-glimmer-30b"
KEYCHAIN_SERVICE = "FIREWORKS_API_KEY"
USER_AGENT = "anamnesis-finetune/0.1"
LORA_RANK = 16  # plan.md. Set explicitly: through REST an omitted rank is sent as 0, full-parameter training.
EPOCHS = 2
MAX_LORA_RANK = 128  # "up to 128; higher values are rejected" (SFT guide)
SPEND_ESTIMATES = {"train": "10.00", "deploy": "16.00", "chat": "0.10"}  # USD on the Fireworks credit
UPLOAD_LIMIT_BYTES = 150_000_000  # the single-request :upload route takes files up to 150 Mb
MIN_EXAMPLES, MAX_EXAMPLES = 3, 3_000_000  # "from 3 to 3 million lines" (SFT guide)
DEFAULT_MAX_TOKENS = 4000  # reasoning tokens count against max_tokens (plan.md)
METRICS_CAP_BYTES = 20_000_000
ROLES = {"system", "user", "assistant", "tool"}
TRANSIENT = {408, 429, 500, 502, 503, 504}
DRY = "(dry run: nothing was sent)"
# Resource ids: 1-63 chars of a-z 0-9 and "-", starting with a letter, not ending with "-".
RESOURCE_ID = re.compile(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?")
LOOKUP_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,62}")  # an existing resource, perhaps made elsewhere
FILE_NAME = re.compile(r"[A-Za-z0-9._-]+\.jsonl")
MODEL_ID = re.compile(r"[A-Za-z0-9._/#:-]{1,300}")


class FireworksError(Exception):
    """A refusal or failure whose message is safe to show: it never contains the API key."""


class ApiError(FireworksError):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class NetworkError(FireworksError):
    """The request got no answer (connection, timeout). Polls retry it."""


# ------------------------------------------------------------------------------------------------ the key
_KEY_CACHE: dict[str, str] = {}  # the key once read, so scrub() can mask it in anything we print


def read_key() -> str:
    """The API key, read from the Keychain when a live call needs it. Never printed, logged or saved."""
    if "key" in _KEY_CACHE:
        return _KEY_CACHE["key"]
    try:
        done = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                              capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.SubprocessError):
        raise FireworksError("could not run `security` to read the key from the Keychain") from None
    key = done.stdout.strip() if done.returncode == 0 else ""
    if not key:
        raise FireworksError(f"the Keychain has no item with the service name {KEYCHAIN_SERVICE}")
    if not re.fullmatch(r"[\x21-\x7e]+", key):  # also keeps a bad key out of http.client's error text
        raise FireworksError("the Keychain item does not look like an API key (unexpected characters)")
    _KEY_CACHE["key"] = key
    return key


def scrub(text: str) -> str:
    """Mask the key, if it has been read, in any text about to be shown."""
    key = _KEY_CACHE.get("key")
    return text.replace(key, "***") if key else text


# ---------------------------------------------------------------------------------------------- validation
def refuse_contributor(value: str) -> str:
    if "-contributor" in value.strip().casefold():
        raise FireworksError("contributor models are not permitted")
    return value


def resource_id(value: str, what: str, *, strict: bool = True) -> str:
    """strict = the creation rule; otherwise any safe id of an existing resource."""
    if not (RESOURCE_ID if strict else LOOKUP_ID).fullmatch(value):
        raise FireworksError(
            f"{what} {value!r} is not a valid id (1-63 chars: a-z 0-9 '-', start with a letter)")
    return value


def account_resource(kind: str, value: str, *, strict: bool = True) -> str:
    """'name' or 'accounts/<account>/<kind>/name' -> the full resource name. Other accounts are refused."""
    prefix = f"accounts/{ACCOUNT}/{kind}/"
    return prefix + resource_id(value.removeprefix(prefix), kind.rstrip("s"), strict=strict)


def short(name: str) -> str:
    return name.rsplit("/", 1)[-1]


# ------------------------------------------------------------------------------------------------ requests
@dataclass(frozen=True)
class Call:
    method: str
    url: str
    body: dict[str, Any] | None = None
    upload: Path | None = None
    label: str = ""
    timeout: float = 60.0


def api(path: str, **query: str | None) -> str:
    params = {key: value for key, value in query.items() if value is not None}
    return f"https://{HOST}/v1/accounts/{ACCOUNT}/{path}" + (f"?{urlencode(params)}" if params else "")


def describe(call: Call) -> str:
    """The request exactly as it would be sent, minus the key."""
    lines = [call.label] if call.label else []
    lines += [f"{call.method} {call.url}",
              f"Authorization: Bearer <{KEYCHAIN_SERVICE} from the Keychain, hidden>"]
    if call.upload is not None:
        size = call.upload.stat().st_size
        lines.append(f"Content-Type: multipart/form-data  file={call.upload.name} ({size} B)")
    elif call.body is not None:
        lines += ["Content-Type: application/json", json.dumps(call.body, indent=2, ensure_ascii=False)]
    return "\n".join(lines)


# Docs: https://docs.fireworks.ai/fine-tuning/fine-tuning-models ("LoRA Rank": with the REST API always set
# loraRank; an omitted rank is sent as 0 and requests full-parameter training; the maximum is 128).
def require_lora_rank(body: dict[str, Any]) -> None:
    rank = body.get("loraRank")
    if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= MAX_LORA_RANK:
        raise FireworksError(f"refusing to create a fine-tuning job without loraRank (1-{MAX_LORA_RANK}): "
                             "an omitted rank means full-parameter training")


def check_call(call: Call) -> None:
    """Refusals that hold for every request, however its body was built."""
    parts = urlparse(call.url)
    if parts.scheme != "https" or parts.hostname != HOST:
        raise FireworksError(f"refusing to send the API key to {parts.hostname or 'a non-https URL'}")
    body = call.body or {}
    for field in ("model", "baseModel", "outputModel"):
        if isinstance(body.get(field), str):
            refuse_contributor(body[field])
    if call.method == "POST" and parts.path.endswith("/supervisedFineTuningJobs"):
        require_lora_rank(body)


# Docs: https://docs.fireworks.ai/api-reference/create-dataset
# Body is {datasetId, dataset}. The client supplies exampleCount (an int64, sent as a string), as in the REST
# example of https://docs.fireworks.ai/fine-tuning/fine-tuning-models ("Restful API").
def create_dataset(name: str, examples: int) -> Call:
    body = {"datasetId": name, "dataset": {"userUploaded": {}, "exampleCount": str(examples)}}
    return Call("POST", api("datasets"), body, label="[1/3] create the dataset entry")


# Docs: https://docs.fireworks.ai/api-reference/upload-dataset-files
# One multipart request with a "file" part, for files up to 150 Mb. The signed-URL route
# (https://docs.fireworks.ai/api-reference/get-dataset-upload-endpoint) is not used: the reference does not
# say which HTTP method and headers the signed URL takes.
def upload_dataset_file(name: str, path: Path) -> Call:
    return Call("POST", api(f"datasets/{name}:upload"), upload=path, timeout=600,
                label="[2/3] upload the file (one multipart request)")


# Docs: https://docs.fireworks.ai/api-reference/get-dataset (state: STATE_UNSPECIFIED, UPLOADING, READY)
def get_dataset(name: str) -> Call:
    return Call("GET", api(f"datasets/{name}"), label="[3/3] poll the dataset until its state is READY")


# Docs: https://docs.fireworks.ai/api-reference/create-supervised-fine-tuning-job
# The OpenAPI body is the job object itself (the page's prose example wraps it in "supervisedFineTuningJob");
# the job id is a query parameter. This is Managed Training: no field picks serverless or dedicated.
# Serverless Training is the Python-SDK Training API (https://docs.fireworks.ai/fine-tuning/training-api/serverless).
def create_sft_job(job_id: str, body: dict[str, Any]) -> Call:
    return Call("POST", api("supervisedFineTuningJobs", supervisedFineTuningJobId=job_id), body)


# Docs: https://docs.fireworks.ai/fine-tuning/fine-tuning-models ("Additional managed training job settings":
# evaluationDataset, epochs, loraRank; the learning rate is left at its default as plan.md says).
def train_body(dataset: str, evaluation: str, output: str) -> dict[str, Any]:
    return {"dataset": dataset, "evaluationDataset": evaluation, "baseModel": BASE_MODEL,
            "outputModel": output, "loraRank": LORA_RANK, "epochs": EPOCHS}


# Docs: https://docs.fireworks.ai/api-reference/get-supervised-fine-tuning-job
def get_sft_job(job: str) -> Call:
    return Call("GET", api(f"supervisedFineTuningJobs/{job}"))


# Docs: https://docs.fireworks.ai/api-reference/match-deployment-shape-versions
# and https://docs.fireworks.ai/faq-new/deployment-infrastructure/what-is-a-deployment-shape
def match_shapes(model: str, addons: bool) -> Call:
    deployment = {"baseModel": model, **({"enableAddons": True} if addons else {})}
    return Call("POST", api("deploymentShapeVersions:match"),
                {"createDeploymentRequest": {"deployment": deployment}})


# Docs: https://docs.fireworks.ai/api-reference/create-deployment
# https://docs.fireworks.ai/fine-tuning/deploying-loras : multi-LoRA deploys the BASE model with enableAddons
# on a BF16 shape (FP8 and FP4 shapes cannot serve addons) and loads the LoRA onto it, so one deployment
# serves the base model and the LoRA. Live merge (--alone) deploys the LoRA model itself and serves the LoRA
# alone; given the base model, --alone is a plain deployment of it.
# https://docs.fireworks.ai/guides/ondemand-deployments : always pass deploymentShape. "default" lets the
# server pick a validated shape and fails rather than override a field we set, so acceleratorCount 1 keeps
# it small.
def create_deployment(model: str, alone: bool, shape: str, deployment_id: str | None) -> Call:
    stock = shape == "default"
    body = {
        "baseModel": model if alone else BASE_MODEL,
        "deploymentShape": shape,
        **({"acceleratorCount": 1} if stock else {}),
        **({"precision": "BF16"} if stock and not alone else {}),
        **({} if alone else {"enableAddons": True}),
        "minReplicaCount": 0,
        "maxReplicaCount": 1,
        "displayName": f"eval {short(model)}"[:63],
    }
    return Call("POST", api("deployments", deploymentId=deployment_id), body,
                label="[1] create the deployment")


# Docs: https://docs.fireworks.ai/api-reference/get-deployment
# (state: CREATING, READY, UPDATING, DELETING, DELETED, FAILED; replicaStats.readyReplicaCount)
def get_deployment(deployment_id: str, label: str = "") -> Call:
    return Call("GET", api(f"deployments/{deployment_id}"), label=label)


# Docs: https://docs.fireworks.ai/api-reference/create-deployed-model (Load LoRA)
def load_lora(model: str, deployment: str) -> Call:
    return Call("POST", api("deployedModels"), {"model": model, "deployment": deployment},
                label="[3] load the LoRA onto the deployment")


# Docs: https://docs.fireworks.ai/api-reference/get-deployed-model (state: DEPLOYING, DEPLOYED, ...)
def get_deployed_model(deployed_id: str) -> Call:
    return Call("GET", api(f"deployedModels/{deployed_id}"), label="[4] poll the LoRA until it is DEPLOYED")


# Docs: https://docs.fireworks.ai/api-reference/delete-deployment
# (ignoreChecks skips the in-use check; the default soft delete already stops the replicas)
def delete_deployment(deployment_id: str, force: bool) -> Call:
    query = {"ignoreChecks": "true"} if force else {}
    return Call("DELETE", api(f"deployments/{deployment_id}", **query), label="[1/2] delete the deployment")


# Docs: https://docs.fireworks.ai/api-reference/post-chatcompletions
# POST https://api.fireworks.ai/inference/v1/chat/completions. reasoning_effort, response_format and the other
# request fields can sit in the messages file.
def chat_call(body: dict[str, Any]) -> Call:
    return Call("POST", f"https://{HOST}/inference/v1/chat/completions", body, timeout=600)


# ------------------------------------------------------------------------------------------------ sending
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib would resend the Authorization header to wherever a redirect points: follow none."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def multipart(path: Path) -> tuple[bytes, str]:
    boundary = "fw" + secrets.token_hex(16)
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n")
    data = head.encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return data, f"multipart/form-data; boundary={boundary}"


def build_request(call: Call, key: str) -> urllib.request.Request:
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": USER_AGENT}
    data, content_type = None, None
    if call.upload is not None:
        data, content_type = multipart(call.upload)
    elif call.body is not None:
        data, content_type = json.dumps(call.body, ensure_ascii=False).encode("utf-8"), "application/json"
    headers |= {"Content-Type": content_type} if content_type else {}
    return urllib.request.Request(call.url, data=data, headers=headers, method=call.method)


def error_text(exc: urllib.error.HTTPError) -> str:
    raw = exc.read(4000).decode("utf-8", "replace").strip()
    try:
        payload = json.loads(raw)
    except ValueError:
        return raw[:500] or str(exc.reason)
    error = payload.get("error", payload) if isinstance(payload, dict) else payload
    return str((error.get("message") if isinstance(error, dict) else error) or raw)[:500]


def http(call: Call, key: str) -> dict[str, Any]:
    """Send one request. Every exception that leaves here is scrubbed and chained to nothing."""
    request = build_request(call, key)
    try:
        with _OPENER.open(request, timeout=call.timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, scrub(error_text(exc))) from None
    except OSError as exc:
        raise NetworkError(f"network error: {scrub(str(getattr(exc, 'reason', exc)))}") from None
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        raise FireworksError("the API answered with something that is not JSON") from None
    return payload if isinstance(payload, dict) else {"result": payload}


# Docs: https://docs.fireworks.ai/api-reference/get-supervised-fine-tuning-job (metricsFileSignedUrl: "the
# signed URL for the metrics file"; its format is not documented there).
def fetch_text(url: str) -> str:
    """GET a signed storage URL. No Authorization header: the key never goes to another host."""
    if urlparse(url).scheme != "https":
        raise FireworksError("the metrics URL is not https: not fetching it")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _OPENER.open(request, timeout=60) as response:
            return response.read(METRICS_CAP_BYTES).decode("utf-8", "replace")
    except OSError:
        raise FireworksError("could not fetch the metrics file (the signed URL may have expired: run status "
                             "again)") from None


def spend_command(estimate: str) -> list[str]:
    return ["uv", "run", "python", "scripts/spend_check.py", "--next", f"fireworks={estimate}"]


def run_spend_gate(estimate: str) -> None:
    """scripts/spend_check.py with the next step's estimate. Any failure stops the step before it sends."""
    sys.stdout.flush()
    try:
        result = subprocess.run(spend_command(estimate), cwd=ROOT, check=False)
    except OSError:
        raise FireworksError("could not run `uv` for the spend gate: nothing was sent") from None
    if result.returncode != 0:
        raise FireworksError(f"the spend gate stopped this step (exit {result.returncode}): nothing was sent")


def say(text: str) -> None:
    print(text, flush=True)


@dataclass(frozen=True)
class Runner:
    """Prints or sends. The only place a request leaves this program, and the only reader of the key."""

    live: bool
    transport: Callable[[Call, str], dict[str, Any]] = http
    fetch: Callable[[str], str] = fetch_text
    gate: Callable[[str], None] = run_spend_gate
    sleep: Callable[[float], None] = time.sleep

    def send(self, call: Call) -> dict[str, Any]:
        check_call(call)
        if not self.live:
            say(describe(call))
            return {}
        return self.transport(call, read_key())

    def spend_gate(self, step: str) -> None:
        if self.live:
            self.gate(SPEND_ESTIMATES[step])
        else:
            say(f"spend gate (runs first with --live): {shlex.join(spend_command(SPEND_ESTIMATES[step]))}")

    def wait(self, call: Call, *, ready: Callable[[dict[str, Any]], bool],
             show: Callable[[dict[str, Any]], str], timeout: float, interval: float,
             gone_ok: bool = False) -> dict[str, Any]:
        """Poll until ready(response); three transient errors in a row are tolerated."""
        # A dry run prints the poll once: looping would only repeat the same request.
        if not self.live:
            say(f"{describe(call)}\n   (live: repeated every {interval:g}s, gives up after {timeout:g}s)")
            return {}
        last: dict[str, Any] = {}
        shown, failures = "", 0
        for _ in range(int(timeout // interval) + 1):
            try:
                last, failures = self.send(call), 0
            except (ApiError, NetworkError) as exc:
                status = getattr(exc, "status", None)  # a network error has none
                if gone_ok and status == 404:
                    return {"state": "GONE (404)"}
                failures += 1
                if failures > 3 or (status is not None and status not in TRANSIENT):
                    raise
            if (line := show(last)) != shown:
                shown = line
                say(line)
            if ready(last):
                return last
            self.sleep(interval)
        raise FireworksError(f"gave up after {timeout:g}s; last seen: {shown or 'nothing'}")


# ------------------------------------------------------------------------------------------------ upload
def check_row(line: str) -> list[str]:
    """What is wrong with one JSONL row."""
    try:
        row = json.loads(line)
    except ValueError:
        return ["not valid JSON"]
    messages = row.get("messages") if isinstance(row, dict) else None
    if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
        return ['needs a non-empty "messages" array of objects']
    problems = []
    if any(m.get("role") not in ROLES for m in messages):
        problems.append(f"role must be one of {sorted(ROLES)}")
    if not any(m.get("role") == "assistant" and m.get("content") for m in messages):
        problems.append("no assistant message with content")
    return problems


# Docs: https://docs.fireworks.ai/fine-tuning/fine-tuning-models ("Prepare a dataset": JSONL, one object per
# line, 3 to 3 million lines, each with a "messages" array of system, user, assistant or tool messages).
def check_dataset_file(path: Path) -> int:
    """Validate the JSONL locally and return the example count, which the client must give Fireworks."""
    if not FILE_NAME.fullmatch(path.name):
        raise FireworksError(f"{path.name}: the file must be named like name.jsonl (letters, digits, . _ -)")
    found, total = [], 0
    try:
        size = path.stat().st_size
        with path.open(encoding="utf-8") as handle:
            for total, line in enumerate(handle, 1):
                found += [f"line {total}: {issue}" for issue in check_row(line)]
    except UnicodeDecodeError:
        raise FireworksError(f"{path.name} is not UTF-8") from None
    except OSError:
        raise FireworksError(f"cannot read {path}") from None
    if found:
        raise FireworksError(f"{path.name}: {len(found)} problems, first: " + "; ".join(found[:5]))
    if not (0 < size <= UPLOAD_LIMIT_BYTES and MIN_EXAMPLES <= total <= MAX_EXAMPLES):
        raise FireworksError(f"{path.name}: {total} examples, {size} bytes; wanted "
                             f"{MIN_EXAMPLES}-{MAX_EXAMPLES} examples and up to 150 Mb")
    say(f"{path.name}: {total} examples, {size} bytes")
    return total


# Docs: https://docs.fireworks.ai/api-reference/get-dataset (response: state, status.code, status.message)
def dataset_ready(dataset: dict[str, Any]) -> bool:
    status = dataset.get("status") or {}
    if status.get("code") not in (None, "OK"):
        raise FireworksError(f"the dataset failed: {status.get('code')}: {status.get('message', '')}")
    return dataset.get("state") == "READY"


def cmd_upload(run: Runner, args: argparse.Namespace) -> None:
    name = resource_id(args.name, "dataset")
    examples = check_dataset_file(args.jsonl)
    run.send(create_dataset(name, examples))
    run.send(upload_dataset_file(name, args.jsonl))
    final = run.wait(get_dataset(name), ready=dataset_ready, timeout=600, interval=3,
                     show=lambda d: f"dataset state: {d.get('state', '?')}")
    say(f"dataset: accounts/{ACCOUNT}/datasets/{name}\nstate: {final.get('state', DRY)}")


# -------------------------------------------------------------------------------------------- train, status
def cmd_train(run: Runner, args: argparse.Namespace) -> None:
    dataset = account_resource("datasets", args.dataset)
    evaluation = account_resource("datasets", args.eval_dataset)
    if dataset == evaluation:
        raise FireworksError("the training and evaluation datasets must differ")
    output = account_resource("models", refuse_contributor(args.output_model))
    run.spend_gate("train")
    job = run.send(create_sft_job(short(output), train_body(dataset, evaluation, output)))
    say(f"job: {job.get('name', DRY)}\nstate: {job.get('state', DRY)}\noutput model: {output}")


# Docs: https://docs.fireworks.ai/api-reference/get-supervised-fine-tuning-job (response: state, status,
# jobProgress, estimatedCost). The job object carries no loss values, only metricsFileSignedUrl.
def show_job(job: dict[str, Any]) -> list[str]:
    status, cost = job.get("status") or {}, job.get("estimatedCost") or {}
    progress = {k: v for k, v in (job.get("jobProgress") or {}).items() if k in ("percent", "epoch")}
    lines = [f"job: {job.get('name', '?')}", f"state: {job.get('state', '?')}"]
    if status.get("message"):
        lines.append(f"status: {status.get('code')}: {status['message']}")
    if progress:
        lines.append("progress: " + ", ".join(f"{k}={v}" for k, v in progress.items()))
    if cost:
        lines.append(f"estimated cost: {cost.get('currencyCode', '')} "
                     f"{float(cost.get('units') or 0) + (cost.get('nanos') or 0) / 1e9:.2f}")
    return lines


def show_metrics(text: str, count: int = 10, width: int = 400) -> list[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    tail = [line if len(line) <= width else line[:width] + "..." for line in lines[-count:]]
    return [f"metrics file: {len(lines)} lines, last {len(tail)}:", *tail]


def cmd_status(run: Runner, args: argparse.Namespace) -> None:
    job = run.send(get_sft_job(resource_id(args.job, "job", strict=False)))
    if not run.live:
        say("then GET the job's metricsFileSignedUrl (a signed URL, fetched without the API key and never\n"
            "printed) and print the last lines of that file, which is where the losses are")
        return
    say("\n".join(show_job(job)))
    url = job.get("metricsFileSignedUrl")
    say("\n".join(show_metrics(run.fetch(url))) if isinstance(url, str) and url else "metrics file: none yet")


# ------------------------------------------------------------------------------------------------ shapes
def gpu_memory_gb(accelerator: str) -> float:
    found = re.search(r"_(\d+)GB", accelerator)
    return float(found.group(1)) if found else float("inf")


# Docs: https://docs.fireworks.ai/api-reference/match-deployment-shape-versions (response: the list
# deploymentShapeVersions, each with name, capabilities and snapshot.acceleratorType/acceleratorCount/
# precision/presetType)
def show_shapes(response: dict[str, Any]) -> list[str]:
    rows = []
    for item in response.get("deploymentShapeVersions") or []:
        shape = item.get("snapshot") or {}
        gpu, count = shape.get("acceleratorType", "?"), shape.get("acceleratorCount") or 0
        detail = (f"{count or '?'} x {gpu}, {shape.get('precision', '?')}, {shape.get('presetType', '?')}, "
                  f"addons: {'MULTI_LORA' in (item.get('capabilities') or [])}")
        total = gpu_memory_gb(gpu) * count if count else float("inf")
        rows.append((total, str(item.get("name", "?")), detail))
    if not rows:
        return ["no validated shapes returned for this model"]
    more = ["(more pages exist and are not shown)"] if response.get("nextPageToken") else []
    return [f"{len(rows)} validated shapes, smallest total GPU memory first (name -> deploy --shape):",
            *[f"  {name}\n      {detail}" for _, name, detail in sorted(rows)], *more]


def cmd_shapes(run: Runner, args: argparse.Namespace) -> None:
    if not args.model.startswith("accounts/") or not MODEL_ID.fullmatch(refuse_contributor(args.model)):
        raise FireworksError("give the full model name, like accounts/fireworks/models/muse-glimmer-30b")
    response = run.send(match_shapes(args.model, args.addons))
    if run.live:
        say("\n".join(show_shapes(response)))


# ------------------------------------------------------------------------------------------------ deploy
# Docs: https://docs.fireworks.ai/api-reference/get-deployment (state, status.message,
# replicaStats.readyReplicaCount: "replicas that are ready and serving traffic")
def deployment_ready(deployment: dict[str, Any]) -> bool:
    state = deployment.get("state")
    if state in ("FAILED", "DELETING", "DELETED"):
        detail = (deployment.get("status") or {}).get("message", "")
        raise FireworksError(f"the deployment is {state}: {detail}")
    serving = (deployment.get("replicaStats") or {}).get("readyReplicaCount")
    return state == "READY" and (serving is None or serving >= 1)


def show_deployment(deployment: dict[str, Any]) -> str:
    stats = deployment.get("replicaStats") or {}
    serving = stats.get("readyReplicaCount", deployment.get("replicaCount", "?"))
    return f"deployment state: {deployment.get('state', '?')}, ready replicas: {serving}"


def created_name(created: dict[str, Any], kind: str, live: bool) -> str:
    name = created.get("name")
    if isinstance(name, str) and name.startswith(f"accounts/{ACCOUNT}/{kind}/"):
        return name
    if live:
        raise FireworksError(f"the response carries no {kind} name: look at the dashboard before retrying")
    return f"accounts/{ACCOUNT}/{kind}/<id from the earlier step>"


def deploy_target(value: str, alone: bool) -> str:
    """Our LoRA, as a bare id or a full name. With --alone any full model name, such as the base model."""
    refuse_contributor(value)
    if alone and value.startswith("accounts/") and value.count("/") == 3 and MODEL_ID.fullmatch(value):
        return value
    return account_resource("models", value)


def deploy_summary(name: str, model: str, alone: bool, ready: dict[str, Any]) -> str:
    keys = ("deploymentShape", "acceleratorType", "acceleratorCount", "precision")
    resolved = ", ".join(f"{k}={ready[k]}" for k in keys if ready.get(k))
    plain = [f"  live-merge form: {model}"] if model.startswith(f"accounts/{ACCOUNT}/") else []
    ids = ([f"  pinned to this deployment: {model}#{name}", *plain] if alone
           else [f"  base model: {BASE_MODEL}#{name}", f"  LoRA: {model}#{name}"])
    return "\n".join([f"deployment: {name}", f"state: {ready.get('state', DRY)}",
                      *([f"shape: {resolved}"] if resolved else []), "model ids to call:", *ids,
                      f"delete it when done: undeploy {short(name)} --live"])


def cmd_deploy(run: Runner, args: argparse.Namespace) -> None:
    model = deploy_target(args.model, args.alone)
    if args.deployment_id:
        resource_id(args.deployment_id, "deployment id")
    run.spend_gate("deploy")
    created = run.send(create_deployment(model, args.alone, args.shape, args.deployment_id))
    name = created_name(created, "deployments", run.live)
    if run.live:
        say(f"deployment: {name}\nstate: {created.get('state', '?')}\n"
            f"it bills while a replica runs: undeploy {short(name)} --live when you are done")
        if not args.alone and not created.get("deploymentShape"):
            say("WARNING: no deploymentShape in the response. The docs say an unvalidated shape is dropped\n"
                "silently and the deployment then rejects addons.")
    try:
        ready = run.wait(get_deployment(short(name), "[2] poll the deployment until READY"),
                         ready=deployment_ready, show=show_deployment, timeout=2400, interval=15)
        if not args.alone:
            loaded = run.send(load_lora(model, name))
            run.wait(get_deployed_model(short(created_name(loaded, "deployedModels", run.live))),
                     ready=lambda d: d.get("state") == "DEPLOYED", timeout=900, interval=10,
                     show=lambda d: f"LoRA state: {d.get('state', '?')}")
    except FireworksError as exc:
        raise FireworksError(f"{exc}\n{name} may still be running and billing: undeploy {short(name)} --live "
                             "(add --force if it says the deployment is in use)") from None
    say(deploy_summary(name, model, args.alone, ready))


def cmd_undeploy(run: Runner, args: argparse.Namespace) -> None:
    deployment = account_resource("deployments", args.deployment, strict=False)
    try:
        run.send(delete_deployment(short(deployment), args.force))
    except ApiError as exc:
        hint = "" if args.force else "\nif it says the deployment is in use, run it again with --force"
        raise FireworksError(f"{exc}{hint}") from None
    final = run.wait(get_deployment(short(deployment), "[2/2] poll until the deployment is deleted"),
                     ready=lambda d: d.get("state") == "DELETED", show=show_deployment, timeout=600,
                     interval=10, gone_ok=True)
    say(f"deployment: {deployment}\nstate: {final.get('state', DRY)}")


# -------------------------------------------------------------------------------------------------- chat
def load_messages(path: Path) -> dict[str, Any]:
    """A JSON list of messages, or an object with "messages" and any other request fields."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise FireworksError(f"{path}: not readable JSON") from None
    body = {"messages": data} if isinstance(data, list) else data
    messages = body.get("messages") if isinstance(body, dict) else None
    if not isinstance(messages, list) or not messages or not all(isinstance(m, dict) for m in messages):
        raise FireworksError(f'{path}: needs a list of messages, or an object with a "messages" list')
    return body


# Docs: https://docs.fireworks.ai/api-reference/post-chatcompletions (response: choices[0].message.content,
# choices[0].finish_reason, usage.prompt_tokens/completion_tokens/total_tokens)
def show_reply(response: dict[str, Any], latency_ms: int) -> list[str]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    lines = ["reply:", message.get("content") or "(empty)"]
    if choice.get("finish_reason") == "length":
        lines.append("WARNING: stopped at max_tokens. Reasoning tokens count against it: raise max_tokens.")
    return [*lines, f"finish_reason: {choice.get('finish_reason')}", f"model: {response.get('model')}",
            f"usage: {json.dumps(response.get('usage'), sort_keys=True)}", f"latency_ms: {latency_ms}"]


def cmd_chat(run: Runner, args: argparse.Namespace) -> None:
    if not MODEL_ID.fullmatch(refuse_contributor(args.model)):
        raise FireworksError("the model id has unexpected characters")
    sent = {key: value for key, value in load_messages(args.messages).items() if key != "model"}
    body = {"model": args.model, "max_tokens": DEFAULT_MAX_TOKENS, **sent}
    run.spend_gate("chat")
    started = time.perf_counter()
    response = run.send(chat_call(body))
    if run.live:
        say("\n".join(show_reply(response, round((time.perf_counter() - started) * 1000))))


# -------------------------------------------------------------------------------------------------- main
COMMANDS = {"upload": cmd_upload, "train": cmd_train, "status": cmd_status, "shapes": cmd_shapes,
            "deploy": cmd_deploy, "undeploy": cmd_undeploy, "chat": cmd_chat}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="finetune/fireworks.py", allow_abbrev=False,
                                     description=(__doc__ or "").split("\n\n")[0])
    common = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    common.add_argument("--live", action="store_true", help="send the requests (default: print them only)")
    commands = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str, *positional: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name, parents=[common], help=help_text, allow_abbrev=False)
        for arg in positional:
            sub.add_argument(arg)
        return sub

    add("upload", "create a dataset, upload a JSONL file, wait for READY",
        "name").add_argument("jsonl", type=Path)
    add("train", f"LoRA SFT of {short(BASE_MODEL)}, rank {LORA_RANK}, {EPOCHS} epochs (job id = model id)",
        "dataset", "eval_dataset", "output_model")
    add("status", "a job's state, progress and the last lines of its metrics file", "job")
    shapes = add("shapes", "validated deployment shapes for a model (read-only)")
    shapes.add_argument("model", nargs="?", default=BASE_MODEL, help="default: the Glimmer base model")
    shapes.add_argument("--addons", action="store_true", help="only shapes that can serve LoRA addons")
    deploy = add("deploy", "on-demand deployment of the base model plus the LoRA (bills per GPU-hour)",
                 "model")
    deploy.add_argument("--alone", "--lora-only", dest="alone", action="store_true",
                        help="serve the model by itself: live merge for a LoRA, or a plain base model")
    deploy.add_argument("--shape", default="default", help="a name from `shapes` (default: server picks)")
    deploy.add_argument("--deployment-id", help="choose the id instead of a generated one")
    add("undeploy", "delete a deployment", "deployment").add_argument(
        "--force", action="store_true", help="skip the in-use check (ignoreChecks=true)")
    add("chat", "one chat-completions call", "model").add_argument("messages", type=Path)
    return parser


def main(argv: list[str] | None = None,
         make_runner: Callable[[bool], Runner] = lambda live: Runner(live)) -> int:
    args = build_parser().parse_args(argv)
    run = make_runner(args.live)
    if not args.live:
        say("DRY RUN: the requests below are printed, not sent. Add --live to send them.")
    try:
        COMMANDS[args.command](run, args)
    except FireworksError as exc:
        print(f"error: {scrub(str(exc))}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted: whatever was already created is still there (see the names printed above)",
              file=sys.stderr)
        return 130
    except Exception as exc:  # whatever happens, the key must not reach the screen
        print(f"error: unexpected {type(exc).__name__}: {scrub(str(exc))}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

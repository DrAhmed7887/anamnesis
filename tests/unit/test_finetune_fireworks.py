"""finetune/fireworks.py: a dry run sends nothing, the refusals hold, and the key never reaches the screen.

Nothing here touches the network, the Keychain or `uv`: every test hands the client a fake transport.
"""

import io
import json
import subprocess
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from finetune import fireworks as fw

KEY = "fw_TESTKEY_abcdef0123456789"
ROW = {"messages": [{"role": "system", "content": "s", "weight": 0},
                    {"role": "user", "content": "u", "weight": 0},
                    {"role": "assistant", "content": "{}", "weight": 1}]}
ACCT = "https://api.fireworks.ai/v1/accounts/<account>"
CHAT = "https://api.fireworks.ai/inference/v1/chat/completions"


def boom(*_args, **_kwargs):
    raise AssertionError("this must not be called")


class Net:
    """Stands in for the network. It records requests and answers the first (method + url) fragment that
    matches. A list is a sequence of answers, the last one repeating; an exception in it is raised."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, call, key):
        self.calls.append(call)
        text = f"{call.method} {call.url}"
        for needle, reply in self.answers:
            if needle in text:
                item = (reply.pop(0) if len(reply) > 1 else reply[0]) if isinstance(reply, list) else reply
                if isinstance(item, Exception):
                    raise item
                return item
        raise AssertionError(f"unexpected request: {text}")

    @property
    def urls(self):
        return [f"{c.method} {c.url.removeprefix(ACCT)}" for c in self.calls]


def invoke(argv, *, net=None, gate=None, fetch=None):
    def make(live):
        return fw.Runner(live, transport=net or boom, fetch=fetch or boom, gate=gate or boom,
                         sleep=lambda _seconds: None)

    return fw.main(argv, make_runner=make)


def body_of(text):
    marker = "Content-Type: application/json\n"
    return json.JSONDecoder().raw_decode(text[text.index(marker) + len(marker):])[0]


@pytest.fixture(autouse=True)
def _fresh_key_cache():
    fw._KEY_CACHE.clear()
    yield
    fw._KEY_CACHE.clear()


@pytest.fixture
def live_key(monkeypatch):
    monkeypatch.setattr(fw, "read_key", lambda: KEY)


@pytest.fixture
def no_key(monkeypatch):
    monkeypatch.setattr(fw, "read_key", boom)


@pytest.fixture
def files(tmp_path):
    jsonl = tmp_path / "claims-train.jsonl"
    jsonl.write_text("\n".join(json.dumps(ROW) for _ in range(3)) + "\n", encoding="utf-8")
    messages = tmp_path / "messages.json"
    messages.write_text(json.dumps([{"role": "user", "content": "hi"}]), encoding="utf-8")
    return jsonl, messages


def fill(argv, files):
    jsonl, messages = files
    return [part.replace("{jsonl}", str(jsonl)).replace("{messages}", str(messages)) for part in argv]


# ------------------------------------------------------------------------------------------------ dry run
DRY = [
    (["upload", "ds-train", "{jsonl}"], f"POST {ACCT}/datasets\n"),
    (["train", "ds-a", "ds-b", "lora-1"],
     f"POST {ACCT}/supervisedFineTuningJobs?supervisedFineTuningJobId=lora-1"),
    (["status", "lora-1"], f"GET {ACCT}/supervisedFineTuningJobs/lora-1"),
    (["shapes"], f"POST {ACCT}/deploymentShapeVersions:match"),
    (["deploy", "lora-1"], f"POST {ACCT}/deployments\n"),
    (["deploy", "lora-1", "--lora-only"], f"POST {ACCT}/deployments\n"),
    (["undeploy", "dep1"], f"DELETE {ACCT}/deployments/dep1"),
    (["chat", "m#d", "{messages}"], f"POST {CHAT}"),
]


@pytest.mark.parametrize(("argv", "request_line"), DRY)
def test_a_dry_run_prints_the_request_and_touches_nothing(argv, request_line, files, no_key, capsys):
    assert invoke(fill(argv, files)) == 0
    out = capsys.readouterr().out
    assert out.startswith("DRY RUN") and request_line in out
    assert "<FIREWORKS_API_KEY from the Keychain, hidden>" in out


def test_train_asks_for_lora_rank_16_and_two_epochs_and_names_its_spend_gate(no_key, capsys):
    assert invoke(["train", "ds-a", "ds-b", "lora-1"]) == 0
    out = capsys.readouterr().out
    assert body_of(out) == {
        "dataset": "accounts/<account>/datasets/ds-a",
        "evaluationDataset": "accounts/<account>/datasets/ds-b",
        "baseModel": "accounts/fireworks/models/muse-glimmer-30b",
        "outputModel": "accounts/<account>/models/lora-1",
        "loraRank": 16, "epochs": 2}
    assert "uv run python scripts/spend_check.py --next fireworks=10.00" in out


def test_deploy_bodies_follow_the_deploying_loras_guide():
    multi = fw.create_deployment("accounts/<account>/models/lora-1", False, "default", None).body
    assert multi["baseModel"] == fw.BASE_MODEL and multi["enableAddons"] is True
    assert (multi["deploymentShape"], multi["acceleratorCount"], multi["precision"]) == ("default", 1, "BF16")
    assert (multi["minReplicaCount"], multi["maxReplicaCount"]) == (0, 1)
    merged = fw.create_deployment("accounts/<account>/models/lora-1", True, "default", None).body
    assert merged["baseModel"] == "accounts/<account>/models/lora-1"
    assert "enableAddons" not in merged and "precision" not in merged
    named = fw.create_deployment("accounts/<account>/models/lora-1", False, "accounts/x/shapes/s", "d1")
    assert "acceleratorCount" not in named.body and "precision" not in named.body
    assert named.url.endswith("/deployments?deploymentId=d1")


def test_chat_takes_its_model_from_the_command_line_and_defaults_max_tokens(tmp_path, no_key, capsys):
    messages = tmp_path / "m.json"
    messages.write_text(json.dumps({"model": "other", "messages": [{"role": "user", "content": "hi"}],
                                    "reasoning_effort": "low"}), encoding="utf-8")
    assert invoke(["chat", "m#d", str(messages)]) == 0
    body = body_of(capsys.readouterr().out)
    assert (body["model"], body["max_tokens"], body["reasoning_effort"]) == ("m#d", 4000, "low")


# --------------------------------------------------------------------------------------------- refusals
@pytest.mark.parametrize("extra", [{}, {"loraRank": 0}, {"loraRank": None}, {"loraRank": True},
                                   {"loraRank": 129}, {"loraRank": "16"}])
@pytest.mark.parametrize("live", [False, True])
def test_a_fine_tuning_job_without_a_lora_rank_is_refused(extra, live):
    call = fw.Call("POST", fw.api("supervisedFineTuningJobs"), {"baseModel": fw.BASE_MODEL, **extra})
    with pytest.raises(fw.FireworksError, match="loraRank"):
        fw.Runner(live, transport=boom).send(call)


def test_train_refuses_one_dataset_for_both_training_and_evaluation(no_key, capsys):
    assert invoke(["train", "ds-a", "accounts/<account>/datasets/ds-a", "lora-1"]) == 1
    assert "must differ" in capsys.readouterr().err


def test_train_refuses_to_send_when_the_rank_goes_missing(monkeypatch, live_key, capsys):
    monkeypatch.setattr(fw, "LORA_RANK", None)
    assert invoke(["train", "ds-a", "ds-b", "lora-1", "--live"], net=boom, gate=lambda _estimate: None) == 1
    assert "loraRank" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [
    ["train", "ds-a", "ds-b", "muse-spark-open-Contributor"],
    ["deploy", "muse-open-contributor-v2"],
    ["chat", "accounts/fireworks/models/muse-spark-open-contributor:latest", "{messages}"],
    ["shapes", "accounts/fireworks/models/muse-glimmer-30b-contributor"],
])
@pytest.mark.parametrize("flags", [[], ["--live"]])
def test_contributor_models_are_refused_before_anything_happens(argv, flags, files, no_key, capsys):
    assert invoke(fill(argv, files) + flags) == 1
    assert "contributor models are not permitted" in capsys.readouterr().err


def test_ids_must_be_valid_and_stay_inside_the_account():
    full = "accounts/<account>/datasets/ds-1"
    assert fw.account_resource("datasets", "ds-1") == fw.account_resource("datasets", full) == full
    for bad in ("1ds", "Ds", "ds_1", "-ds", "ds-", "a" * 64, "accounts/other/datasets/ds-1", "../x", ""):
        with pytest.raises(fw.FireworksError):
            fw.account_resource("datasets", bad)
    assert fw.account_resource("deployments", "3f9a", strict=False).endswith("/3f9a")  # a generated id


@pytest.mark.parametrize("url", ["https://evil.example/v1/x", f"http://{fw.HOST}/v1/x", "file:///etc/passwd"])
def test_the_key_goes_only_to_the_fireworks_host_over_https(url):
    with pytest.raises(fw.FireworksError, match="refusing to send the API key"):
        fw.Runner(True, transport=boom).send(fw.Call("GET", url))


# ------------------------------------------------------------------------------------------------ upload
@pytest.mark.parametrize(("content", "problem"), [
    ("not json\n" * 3, "not valid JSON"),
    ('{"x": 1}\n' * 3, "messages"),
    ('{"messages": [{"role": "user", "content": "u"}]}\n' * 3, "no assistant message"),
    ('{"messages": [{"role": "robot", "content": "u"}]}\n' * 3, "role must be one of"),
    (json.dumps(ROW) + "\n\n", "line 2"),
    (json.dumps(ROW) + "\n" + json.dumps(ROW) + "\n", "wanted 3-3000000"),
])
def test_upload_refuses_a_bad_file(tmp_path, content, problem, capsys):
    bad = tmp_path / "bad.jsonl"
    bad.write_text(content, encoding="utf-8")
    assert invoke(["upload", "ds-a", str(bad)]) == 1
    assert problem in capsys.readouterr().err


def test_upload_refuses_a_misnamed_or_non_utf8_file(tmp_path, capsys):
    misnamed = tmp_path / "data.json"
    misnamed.write_text(json.dumps(ROW) + "\n", encoding="utf-8")
    assert invoke(["upload", "ds-a", str(misnamed)]) == 1
    assert "name.jsonl" in capsys.readouterr().err
    latin = tmp_path / "x.jsonl"
    latin.write_bytes(b'{"messages": "\xff"}\n' * 3)
    assert invoke(["upload", "ds-a", str(latin)]) == 1
    assert "not UTF-8" in capsys.readouterr().err


def test_upload_live_creates_uploads_and_waits_for_ready(files, live_key, capsys):
    net = Net(("GET", [{"state": "UPLOADING"}, {"state": "READY"}]), (":upload", {"id": "ds-train"}),
              ("POST", {"name": "accounts/<account>/datasets/ds-train", "state": "UPLOADING"}))
    assert invoke(fill(["upload", "ds-train", "{jsonl}", "--live"], files), net=net) == 0
    assert net.urls == ["POST /datasets", "POST /datasets/ds-train:upload", "GET /datasets/ds-train",
                        "GET /datasets/ds-train"]
    assert net.calls[0].body["dataset"]["exampleCount"] == "3" and net.calls[1].upload == files[0]
    assert "state: READY" in capsys.readouterr().out


def test_a_failed_dataset_stops_the_wait(files, live_key, capsys):
    failed = {"state": "UPLOADING", "status": {"code": "INVALID_ARGUMENT", "message": "line 2 is broken"}}
    net = Net(("GET", failed), (":upload", {}), ("POST", {}))
    assert invoke(fill(["upload", "ds-train", "{jsonl}", "--live"], files), net=net) == 1
    assert "line 2 is broken" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------- spend gate
def paid_net():
    return Net(
        ("chat/completions", {"model": "m", "choices": [{"message": {"content": "ok"}}], "usage": {}}),
        ("supervisedFineTuningJobs", {"name": "accounts/<account>/supervisedFineTuningJobs/lora-1"}),
        (f"GET {ACCT}/deployedModels/dm1", {"state": "DEPLOYED"}),
        ("deployedModels", {"name": "accounts/<account>/deployedModels/dm1"}),
        (f"GET {ACCT}/deployments/dep1", {"state": "READY", "replicaStats": {"readyReplicaCount": 1}}),
        ("deployments", {"name": "accounts/<account>/deployments/dep1", "deploymentShape": "s"}),
    )


PAID = [(["train", "ds-a", "ds-b", "lora-1"], "10.00"), (["deploy", "lora-1"], "16.00"),
        (["chat", "m#d", "{messages}"], "0.10")]


@pytest.mark.parametrize(("argv", "estimate"), PAID)
def test_paid_steps_run_the_spend_gate_once_before_the_first_request(argv, estimate, files, live_key):
    events, net = [], paid_net()

    def logged(call, key):
        events.append(("send", call.method))
        return net(call, key)

    assert invoke(fill(argv, files) + ["--live"], net=logged, gate=lambda e: events.append(("gate", e))) == 0
    assert events[0] == ("gate", estimate) and [e for e in events if e[0] == "gate"] == [("gate", estimate)]
    assert len(events) > 1


@pytest.mark.parametrize(("argv", "estimate"), PAID)
def test_a_failing_spend_gate_stops_the_step_before_anything_is_sent(argv, estimate, files, live_key, capsys):
    def refuse(_estimate):
        raise fw.FireworksError("the spend gate stopped this step (exit 1): nothing was sent")

    assert invoke(fill(argv, files) + ["--live"], net=boom, gate=refuse) == 1
    assert "spend gate" in capsys.readouterr().err


def test_the_gate_runs_spend_check_with_the_estimate_and_stops_on_any_failure(monkeypatch):
    seen = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs["cwd"]))
        return subprocess.CompletedProcess(command, 0 if len(seen) == 1 else 1)

    monkeypatch.setattr(fw.subprocess, "run", fake_run)
    fw.run_spend_gate("16.00")
    command = ["uv", "run", "python", "scripts/spend_check.py", "--next", "fireworks=16.00"]
    assert seen[0] == (command, fw.ROOT)
    with pytest.raises(fw.FireworksError, match="spend gate stopped"):
        fw.run_spend_gate("16.00")
    monkeypatch.setattr(fw.subprocess, "run", boom)
    with pytest.raises(AssertionError):  # only an OSError (no uv) becomes a refusal; anything else is a bug
        fw.run_spend_gate("16.00")


@pytest.mark.parametrize(("argv", "net"), [
    (["status", "lora-1"], Net(("GET", {"state": "JOB_STATE_RUNNING"}))),
    (["shapes"], Net(("POST", {}))),
    (["undeploy", "dep1"], Net(("DELETE", {}), ("GET", {"state": "DELETED"}))),
])
def test_free_steps_never_run_the_spend_gate(argv, net, live_key):
    assert invoke([*argv, "--live"], net=net) == 0


# --------------------------------------------------------------------------------------------- the key
def test_the_key_is_read_from_the_keychain_and_masked_in_every_message(monkeypatch, capsys):
    commands = []

    def keychain(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=KEY + "\n", stderr="")

    monkeypatch.setattr(fw.subprocess, "run", keychain)
    net = Net(("GET", fw.ApiError(500, f"server said {KEY}")))
    assert invoke(["status", "lora-1", "--live"], net=net) == 1
    streams = capsys.readouterr()
    assert commands == [["security", "find-generic-password", "-s", "FIREWORKS_API_KEY", "-w"]]
    assert KEY not in streams.out + streams.err and "server said ***" in streams.err


def test_a_dry_run_never_reads_the_key(files, no_key, capsys):
    for argv, _ in DRY:
        assert invoke(fill(argv, files)) == 0
    assert KEY not in capsys.readouterr().out


@pytest.mark.parametrize(("stdout", "code", "message"), [
    ("", 44, "no item"),
    (f"{KEY} with spaces\n", 0, "unexpected characters"),
    (f"{KEY}\nx", 0, "unexpected characters"),
])
def test_a_missing_or_malformed_key_is_refused_without_echoing_it(monkeypatch, stdout, code, message):
    def keychain(command, **_kwargs):
        return subprocess.CompletedProcess(command, code, stdout=stdout)

    monkeypatch.setattr(fw.subprocess, "run", keychain)
    with pytest.raises(fw.FireworksError, match=message) as caught:
        fw.read_key()
    assert KEY not in str(caught.value)


class FakeOpener:
    def __init__(self, outcome):
        self.outcome, self.requests = outcome, []

    def open(self, request, timeout=None):
        self.requests.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return io.BytesIO(self.outcome)


def test_http_sends_the_bearer_key_and_masks_it_in_errors(monkeypatch):
    fw._KEY_CACHE["key"] = KEY
    ok = FakeOpener(b'{"state": "READY"}')
    monkeypatch.setattr(fw, "_OPENER", ok)
    assert fw.http(fw.Call("GET", fw.api("datasets/x")), KEY) == {"state": "READY"}
    assert ok.requests[0].get_header("Authorization") == f"Bearer {KEY}"
    payload = io.BytesIO(json.dumps({"message": f"bad {KEY}"}).encode())
    monkeypatch.setattr(fw, "_OPENER", FakeOpener(urllib.error.HTTPError("u", 401, "no", {}, payload)))
    with pytest.raises(fw.ApiError) as api_error:
        fw.http(fw.Call("GET", fw.api("datasets/x")), KEY)
    shown = str(api_error.value)
    assert api_error.value.status == 401 and KEY not in shown and "bad ***" in shown
    monkeypatch.setattr(fw, "_OPENER", FakeOpener(urllib.error.URLError(f"reset {KEY}")))
    with pytest.raises(fw.NetworkError) as network_error:
        fw.http(fw.Call("GET", fw.api("datasets/x")), KEY)
    assert KEY not in str(network_error.value)


def test_a_redirect_is_never_followed_because_urllib_would_resend_the_key():
    assert fw._NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://evil.example/") is None


@pytest.fixture
def local_server():
    """A throwaway localhost server that records requests. Not a Fireworks call: http() takes any URL."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def handle_any(self):
            length = int(self.headers.get("Content-Length") or 0)
            seen.append((self.command, self.path, dict(self.headers), self.rfile.read(length)))
            redirect = self.path == "/redirect"
            payload = b"" if redirect else b'{"ok": true}'
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header("Location", f"http://127.0.0.1:{self.server.server_address[1]}/leak")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = do_POST = handle_any

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", seen
    server.shutdown()
    server.server_close()


def test_http_over_a_real_socket_sends_json_and_multipart_and_refuses_a_redirect(local_server, tmp_path):
    base, seen = local_server
    assert fw.http(fw.Call("POST", base + "/json", {"text": "ضغط ١٠"}), KEY) == {"ok": True}
    _, _, headers, body = seen[-1]
    assert headers["Authorization"] == f"Bearer {KEY}" and headers["Content-Type"] == "application/json"
    assert json.loads(body.decode("utf-8")) == {"text": "ضغط ١٠"}
    upload = tmp_path / "x.jsonl"
    upload.write_bytes(b'{"messages": []}\n')
    fw.http(fw.Call("POST", base + "/upload", upload=upload), KEY)
    _, _, headers, body = seen[-1]
    boundary = headers["Content-Type"].split("boundary=")[1]
    assert headers["Content-Type"].startswith("multipart/form-data;")
    assert body.endswith(f"--{boundary}--\r\n".encode()) and int(headers["Content-Length"]) == len(body)
    assert b'name="file"; filename="x.jsonl"' in body and b'{"messages": []}\n' in body
    with pytest.raises(fw.ApiError) as redirected:
        fw.http(fw.Call("GET", base + "/redirect"), KEY)
    assert redirected.value.status == 302 and all(path != "/leak" for _, path, _, _ in seen)


# ------------------------------------------------------------------------------------------------ polling
def poll(net, **kwargs):
    run = fw.Runner(True, transport=net, sleep=lambda _seconds: None)
    return run.wait(fw.get_dataset("ds"), ready=lambda d: d.get("state") == "READY",
                    show=lambda d: str(d.get("state")), timeout=30, interval=10, **kwargs)


def test_polls_tolerate_three_transient_errors_in_a_row(live_key):
    answers = [fw.ApiError(503, "x"), fw.NetworkError("n"), fw.ApiError(429, "x"), {"state": "READY"}]
    net = Net(("GET", answers))
    assert poll(net)["state"] == "READY" and len(net.calls) == 4


def test_polls_stop_on_the_fourth_transient_error_a_hard_error_or_a_timeout(live_key):
    with pytest.raises(fw.ApiError):
        poll(Net(("GET", fw.ApiError(503, "x"))))
    hard = Net(("GET", fw.ApiError(400, "bad")))
    with pytest.raises(fw.ApiError):
        poll(hard)
    assert len(hard.calls) == 1
    slow = Net(("GET", {"state": "UPLOADING"}))
    with pytest.raises(fw.FireworksError, match="gave up after 30s"):
        poll(slow)
    assert len(slow.calls) == 4


def test_a_404_while_waiting_for_a_deletion_means_it_is_gone(live_key):
    assert poll(Net(("GET", fw.ApiError(404, "gone"))), gone_ok=True) == {"state": "GONE (404)"}


# ------------------------------------------------------------------------------------ status, shapes, chat
def test_status_prints_the_state_and_the_tail_of_the_metrics_file_but_never_the_signed_url(live_key, capsys):
    job = {"name": "accounts/<account>/supervisedFineTuningJobs/lora-1", "state": "JOB_STATE_COMPLETED",
           "jobProgress": {"percent": 100, "epoch": 2}, "metricsFileSignedUrl": "https://storage.example/m?sig=SECRET",
           "estimatedCost": {"currencyCode": "USD", "units": "0", "nanos": 250_000_000}}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return "\n".join(f'{{"step": {n}, "loss": {n / 10}}}' for n in range(1, 26)) + "\n"

    assert invoke(["status", "lora-1", "--live"], net=Net(("GET", job)), fetch=fetch) == 0
    out = capsys.readouterr().out
    assert fetched == ["https://storage.example/m?sig=SECRET"] and "SECRET" not in out
    assert "state: JOB_STATE_COMPLETED" in out and "progress: percent=100, epoch=2" in out
    assert "estimated cost: USD 0.25" in out and "metrics file: 25 lines, last 10:" in out
    assert '"step": 25' in out and '"step": 16' in out and '"step": 15' not in out


def test_status_says_so_when_there_is_no_metrics_file_yet(live_key, capsys):
    assert invoke(["status", "lora-1", "--live"], net=Net(("GET", {"state": "JOB_STATE_PENDING"}))) == 0
    assert "metrics file: none yet" in capsys.readouterr().out


@pytest.mark.parametrize("url", ["http://storage.example/m", "file:///etc/passwd", "ftp://x/m"])
def test_the_metrics_file_is_only_fetched_over_https(url):
    with pytest.raises(fw.FireworksError, match="not https"):
        fw.fetch_text(url)


def test_shapes_lists_the_smallest_total_gpu_memory_first(live_key, capsys):
    def shape(name, gpu, count, caps):
        return {"name": f"accounts/fireworks/deploymentShapes/{name}/versions/1", "capabilities": caps,
                "snapshot": {"acceleratorType": gpu, "acceleratorCount": count, "precision": "BF16",
                             "presetType": "MINIMAL"}}

    answer = {"deploymentShapeVersions": [shape("big", "NVIDIA_H200_141GB", 2, ["MULTI_LORA"]),
                                          shape("mystery", "NVIDIA_GB200", 1, []),
                                          shape("small", "NVIDIA_H100_80GB", 1, ["MULTI_LORA"])]}
    assert invoke(["shapes", "--addons", "--live"], net=Net(("POST", answer))) == 0
    out = capsys.readouterr().out
    assert out.index("/small/") < out.index("/big/") < out.index("/mystery/")
    assert "1 x NVIDIA_H100_80GB, BF16, MINIMAL, addons: True" in out


def test_chat_prints_the_reply_usage_and_latency(files, live_key, capsys):
    reply = {"model": "m", "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
             "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}]}
    net = Net(("chat/completions", reply))
    assert invoke(fill(["chat", "m#d", "{messages}", "--live"], files), net=net, gate=lambda _e: None) == 0
    out = capsys.readouterr().out
    assert "reply:\nhello" in out and "finish_reason: stop" in out and "latency_ms: " in out
    assert 'usage: {"completion_tokens": 2, "prompt_tokens": 5, "total_tokens": 7}' in out
    assert net.calls[0].body["model"] == "m#d" and net.calls[0].body["messages"][0]["content"] == "hi"


def test_chat_warns_when_reasoning_used_up_max_tokens(files, live_key, capsys):
    reply = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}], "usage": {}}
    assert invoke(fill(["chat", "m#d", "{messages}", "--live"], files), net=Net(("chat", reply)),
                  gate=lambda _e: None) == 0
    assert "raise max_tokens" in capsys.readouterr().out


# ------------------------------------------------------------------------------------ deploy, undeploy
def test_deploy_live_creates_waits_loads_the_lora_and_prints_the_model_ids(files, live_key, capsys):
    net = paid_net()
    assert invoke(["deploy", "lora-1", "--live"], net=net, gate=lambda _e: None) == 0
    assert net.urls == ["POST /deployments", "GET /deployments/dep1", "POST /deployedModels",
                        "GET /deployedModels/dm1"]
    assert net.calls[2].body == {"model": "accounts/<account>/models/lora-1",
                                 "deployment": "accounts/<account>/deployments/dep1"}
    out = capsys.readouterr().out
    assert "deployment: accounts/<account>/deployments/dep1" in out and "undeploy dep1 --live" in out
    assert f"{fw.BASE_MODEL}#accounts/<account>/deployments/dep1" in out
    assert "accounts/<account>/models/lora-1#accounts/<account>/deployments/dep1" in out


def test_deploy_lora_only_loads_nothing(files, live_key, capsys):
    net = paid_net()
    assert invoke(["deploy", "lora-1", "--lora-only", "--live"], net=net, gate=lambda _e: None) == 0
    assert net.urls == ["POST /deployments", "GET /deployments/dep1"]
    out = capsys.readouterr().out
    assert "live-merge form: accounts/<account>/models/lora-1\n" in out
    pinned = "accounts/<account>/models/lora-1#accounts/<account>/deployments/dep1"
    assert f"pinned to this deployment: {pinned}" in out


def test_alone_also_deploys_the_plain_base_model_and_without_it_only_our_models_are_allowed(no_key, capsys):
    assert invoke(["deploy", fw.BASE_MODEL, "--alone"]) == 0
    out = capsys.readouterr().out
    body = body_of(out)
    assert body["baseModel"] == fw.BASE_MODEL and body["acceleratorCount"] == 1
    assert "enableAddons" not in body and "precision" not in body
    assert body["displayName"] == "eval muse-glimmer-30b"
    assert f"pinned to this deployment: {fw.BASE_MODEL}#" in out and "live-merge form" not in out
    assert invoke(["deploy", fw.BASE_MODEL]) == 1  # a full name outside the account needs --alone
    assert "not a valid id" in capsys.readouterr().err
    assert invoke(["deploy", "accounts/fireworks/models/x-contributor", "--alone"]) == 1
    assert "contributor models are not permitted" in capsys.readouterr().err


def test_a_deployment_that_fails_after_creation_says_how_to_delete_it(live_key, capsys):
    net = Net((f"GET {ACCT}/deployments/dep1", {"state": "FAILED", "status": {"message": "no GPU"}}),
              ("deployments", {"name": "accounts/<account>/deployments/dep1", "deploymentShape": "s"}))
    assert invoke(["deploy", "lora-1", "--live"], net=net, gate=lambda _e: None) == 1
    err = capsys.readouterr().err
    assert "no GPU" in err and "undeploy dep1 --live" in err


def test_deploy_warns_when_the_shape_was_dropped(live_key, capsys):
    net = paid_net()
    net.answers[-1] = ("deployments", {"name": "accounts/<account>/deployments/dep1"})
    assert invoke(["deploy", "lora-1", "--live"], net=net, gate=lambda _e: None) == 0
    assert "no deploymentShape in the response" in capsys.readouterr().out


def test_undeploy_deletes_then_waits_for_the_deletion(live_key, capsys):
    net = Net(("DELETE", {}), ("GET", [{"state": "DELETING"}, {"state": "DELETED"}]))
    assert invoke(["undeploy", "dep1", "--live"], net=net) == 0
    assert net.urls == ["DELETE /deployments/dep1", "GET /deployments/dep1", "GET /deployments/dep1"]
    assert "state: DELETED" in capsys.readouterr().out


def test_undeploy_suggests_force_only_when_the_deployment_is_in_use(live_key, capsys):
    net = Net(("DELETE", fw.ApiError(400, "deployment is in use")))
    assert invoke(["undeploy", "dep1", "--live"], net=net) == 1
    assert "run it again with --force" in capsys.readouterr().err
    forced = Net(("DELETE", {}), ("GET", fw.ApiError(404, "gone")))
    assert invoke(["undeploy", "dep1", "--force", "--live"], net=forced) == 0
    assert forced.urls[0] == "DELETE /deployments/dep1?ignoreChecks=true"

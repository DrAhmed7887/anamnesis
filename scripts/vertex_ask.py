"""One prompt to Gemini on Vertex AI, billed to the gcloud project's billing account.

    uv run python scripts/vertex_ask.py <prompt-file> [--model gemini-4-argon] [--thinking medium]

The QM's fallback route: scripts/qm.sh uses it when Antigravity's quota is used up (QM_VIA=vertex).
Auth comes from the active gcloud account (`gcloud auth print-access-token`) and the project from
`gcloud config get-value project`; nothing is stored. The reply goes to stdout; tokens and an
estimated cost go to stderr. Prices are Google's published Gemini 4 Argon rates per 1M tokens
(input $2, output and thinking $10) until 30 Nov 2026; Cloud Billing is the final word.
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

PRICE_PER_M = {"input": Decimal(2), "output": Decimal(10)}
LEDGER = Path(__file__).resolve().parents[1] / "evidence/spend/google_ledger.jsonl"  # read by spend_check.py


def gcloud(*args: str) -> str:
    return subprocess.run(["gcloud", *args], capture_output=True, text=True, check=True).stdout.strip()


def ask(prompt: str, model: str, thinking: str) -> dict:
    project = gcloud("config", "get-value", "project")
    url = (f"https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/"
           f"publishers/google/models/{model}:generateContent")
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"thinkingConfig": {"thinkingLevel": thinking}}}
    headers = {"Authorization": f"Bearer {gcloud('auth', 'print-access-token')}",
               "Content-Type": "application/json"}
    request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        sys.exit(f"vertex: HTTP {exc.code}: {exc.read().decode(errors='replace')[:600]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt_file")
    parser.add_argument("--model", default="gemini-4-argon")
    parser.add_argument("--thinking", default="medium")
    args = parser.parse_args()
    with open(args.prompt_file, encoding="utf-8") as stream:
        reply = ask(stream.read(), args.model, args.thinking)
    parts = reply["candidates"][0]["content"]["parts"]
    print("".join(part.get("text", "") for part in parts if not part.get("thought")))
    usage = reply.get("usageMetadata", {})
    prompt_tokens = usage.get("promptTokenCount", 0)
    thinking_tokens = usage.get("thoughtsTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0) + thinking_tokens
    cost = (prompt_tokens * PRICE_PER_M["input"] + output_tokens * PRICE_PER_M["output"]) / 1_000_000
    print(f"vertex {reply.get('modelVersion', args.model)}: {prompt_tokens} input, {output_tokens} output "
          f"(thinking {thinking_tokens}) -> ${cost:.5f} est.", file=sys.stderr)
    line = {"model_id": reply.get("modelVersion", args.model), "input_tokens": prompt_tokens,
            "output_tokens": output_tokens, "cost_usd": str(cost.quantize(Decimal("0.00001"))),
            "estimated": True, "at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    with LEDGER.open("a", encoding="utf-8") as ledger:
        ledger.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    main()

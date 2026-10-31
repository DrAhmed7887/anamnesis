"""Serve the r1 Glimmer LoRA on Modal for the product's optional claim extractor.

Deploy it:

    ~/.local/bin/modal deploy finetune/modal_serve.py

Then warm it up: GET /health with the proxy token in an Authorization header, waiting up to 10 minutes for
the container to load the weights and the adapter. Only the synthetic-voice transcripts of staged cases go
to this endpoint (docs/DATA_HANDLING.md).
"""

import sys
import uuid
from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import glimmer  # noqa: E402
import modal_glimmer  # noqa: E402

app = modal.App("anamnesis-glimmer-serve")
image = modal_glimmer.eval_image.add_local_file(HERE / "modal_glimmer.py", "/root/modal_glimmer.py")


def _valid_body(body) -> tuple | None:
    """The extract request's (messages, schema, max_tokens), or None for a bad body."""
    if not isinstance(body, dict):
        return None
    messages, schema, max_tokens = body.get("messages"), body.get("schema"), body.get("max_tokens")
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or not all(isinstance(message, dict) for message in messages)
        or messages[0].get("role") != "system"
        or messages[1].get("role") != "user"
        or not all(
            isinstance(message.get("content"), str) and message["content"]
            for message in messages
        )
    ):
        return None
    if not isinstance(schema, dict):
        return None
    if type(max_tokens) is not int or not 1 <= max_tokens <= 16000:
        return None
    return messages, schema, max_tokens


@app.cls(
    image=image,
    gpu=glimmer.GPU,
    timeout=600,
    scaledown_window=600,
    max_containers=1,
    **modal_glimmer.MACHINE,
)
class Server:
    @modal.enter()
    def load(self) -> None:
        from vllm import LLM
        from vllm.lora.request import LoRARequest

        modal_glimmer.runs.reload()
        self.llm = LLM(
            model=modal_glimmer.WEIGHTS,
            enable_lora=True,
            max_lora_rank=glimmer.LORA["r"],
            max_loras=1,
            max_model_len=glimmer.MAX_MODEL_LEN,
            limit_mm_per_prompt={"image": 0, "video": 0},
            seed=glimmer.EVAL_SEED,
        )
        self.tokenizer = self.llm.get_tokenizer()
        self.lora = LoRARequest("r1", 1, "/runs/r1/adapter")

    @modal.asgi_app(requires_proxy_auth=True)
    def web(self):
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse

        web_app = FastAPI()

        @web_app.get("/health")
        def health():
            return {"ready": True, "adapter": "r1", "revision": glimmer.REVISION}

        @web_app.post("/extract")
        async def extract(request: Request):
            try:
                body = await request.json()
            except Exception:
                return JSONResponse({"error": "bad extract body"}, status_code=400)
            checked = _valid_body(body)
            if checked is None:
                return JSONResponse({"error": "bad extract body"}, status_code=400)
            messages, schema, max_tokens = checked
            messages = [{"role": m["role"], "content": m["content"]} for m in messages]
            prompt_tokens = len(glimmer.prompt_ids(self.tokenizer, messages))
            if prompt_tokens + max_tokens > glimmer.MAX_MODEL_LEN:
                return JSONResponse({"error": "bad extract body"}, status_code=400)
            row = modal_glimmer._two_passes(
                self.llm, self.tokenizer, [messages], self.lora, schema, max_tokens
            )["rows"][0]
            return {
                "id": uuid.uuid4().hex,
                "reply": row["reply"],
                "opened_answer": row["opened_answer"],
                "first_finish": row["first_finish"],
                "answer_finish": row.get("answer_finish"),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": row["first_tokens"] + row.get("answer_tokens", 0),
            }

        return web_app

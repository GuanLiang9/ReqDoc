"""The only module that talks to a model. Phase 2 adds BedrockClient with the same interface."""
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from . import config

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


def llm_schema(model: type[BaseModel]) -> dict:
    """JSON schema for the model with EVERY property required.

    With optional properties a small model happily skips whole lists (it returned no requirements at all),
    so the model must emit every key. Python-side validation still uses the original model.
    """
    def require_all(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["required"] = list(node["properties"])
            for v in node.values():
                require_all(v)
        elif isinstance(node, list):
            for v in node:
                require_all(v)

    schema = model.model_json_schema()
    require_all(schema)
    return schema


class LLMClient(Protocol):
    def generate_json(self, system: str, user: str, schema: type[T]) -> T: ...


class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None, num_ctx: int | None = None):
        self.host = host or config.OLLAMA_HOST
        self.model = model or config.OLLAMA_MODEL
        self.num_ctx = num_ctx or config.OLLAMA_NUM_CTX
        self.num_gpu = config.OLLAMA_NUM_GPU
        self._client = None

    def _get_client(self):
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self.host)
        return self._client

    def generate_json(self, system: str, user: str, schema: type[T]) -> T:
        """Schema-constrained call, temperature 0. Retries once with the validation error."""
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        # num_predict stops a looping model from generating for minutes
        options = {"temperature": 0, "num_ctx": self.num_ctx, "num_predict": config.OLLAMA_MAX_TOKENS}
        if self.num_gpu is not None:
            options["num_gpu"] = self.num_gpu
        last_error = ""
        for _ in range(2):
            try:
                resp = self._get_client().chat(
                    model=self.model,
                    messages=messages,
                    format=llm_schema(schema),
                    options=options,
                )
            except Exception as e:  # connection refused, model missing, etc.
                raise LLMError(self._explain(e)) from e
            content = resp["message"]["content"]
            try:
                return schema.model_validate_json(content)
            except ValidationError as e:
                last_error = str(e)
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"That JSON was invalid: {last_error}\nReturn corrected JSON only."},
                ]
        raise LLMError(f"Model returned invalid JSON twice. Try a larger model.\n{last_error}")

    def _explain(self, e: Exception) -> str:
        text = str(e)
        if "not found" in text.lower():
            return f"Model '{self.model}' not found. Run: ollama pull {self.model}"
        if "connect" in text.lower():
            return f"Cannot connect to Ollama at {self.host}. Start Ollama (system tray) or run: ollama serve"
        return f"Ollama error: {text}"

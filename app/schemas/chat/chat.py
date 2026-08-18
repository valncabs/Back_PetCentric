from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, field_validator


class ChatRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La pregunta no puede estar vacía.")
        if len(value) > 2000:
            raise ValueError("La pregunta no puede superar los 2000 caracteres.")
        return value


class ChatSource(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool: str
    result: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []


class ProxyUrlUpdate(BaseModel):
    proxy_url: str

    @field_validator("proxy_url")
    @classmethod
    def proxy_url_is_public_http(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("Debe ser una URL http(s) pública del proxy de herramientas.")
        if parts.hostname in ("127.0.0.1", "localhost", "0.0.0.0", "::1"):
            raise ValueError("Render no alcanza localhost: la URL debe ser pública.")
        if len(value) > 500:
            raise ValueError("La URL es demasiado larga (máx. 500 caracteres).")
        return value
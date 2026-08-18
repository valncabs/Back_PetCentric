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
import json
import logging

import httpx

from app.core.config import settings
from app.core.exceptions import AiBridgeException
from app.schemas.chat.chat import ChatResponse, ChatSource
from app.services.proxy_registry import get_proxy_url

_log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres Pet AI, el asistente virtual de Pet-Centric, la plataforma de mascotas "
    "perdidas y encontradas. Respondes preguntas sobre los datos de la plataforma "
    "consultando la base de datos con las herramientas disponibles. Cuando uses una "
    "herramienta, responde en español con una frase natural citando el número real "
    "que devolvió el tool. Responde siempre en texto plano, sin markdown "
    "(sin asteriscos, cursivas ni negritas). Si no puedes responder, dilo con honestidad."
)

MAX_TOOL_ROUNDS = 4


class ChatService:
    """Puente IA: function-calling con Groq + ejecución de herramientas vía mcpo."""

    def __init__(self) -> None:
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = settings.GROQ_MODEL
        self.proxy_url = get_proxy_url()
        self.proxy_key = settings.AI_TOOL_PROXY_KEY
        self._tools_cache: list[dict] | None = None

        if not self.proxy_url.startswith(("http://", "https://")):
            _log.error(
                "La URL del proxy de herramientas no empieza con http(s)://: '%s'",
                self.proxy_url,
            )
            raise AiBridgeException(
                "La URL del proxy de herramientas (AI_TOOL_PROXY_URL) "
                "no empieza con http:// o https://."
            )

    async def ask(self, question: str) -> ChatResponse:
        if not settings.GROQ_API_KEY:
            raise AiBridgeException("GROQ_API_KEY no está configurada en el backend.")

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        sources: list[ChatSource] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            tools = await self._load_tools(client)
            for _ in range(MAX_TOOL_ROUNDS):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                }
                try:
                    response = await client.post(
                        self.groq_url,
                        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                        json=payload,
                    )
                except httpx.TimeoutException:
                    _log.error("Groq no respondió a tiempo (%s)", self.groq_url)
                    raise AiBridgeException(
                        "El proveedor de IA tardó demasiado en responder."
                    )
                except httpx.HTTPError as e:
                    _log.error(
                        "No se pudo conectar con Groq en %s: %s", self.groq_url, e
                    )
                    raise AiBridgeException(
                        f"No se pudo conectar con el proveedor de IA: {e}"
                    )
                if response.status_code >= 400:
                    _log.error(
                        "Groq respondió %s: %s", response.status_code, response.text[:500]
                    )
                    raise AiBridgeException("El proveedor de IA respondió con un error.")

                choice = response.json()["choices"][0]
                message = choice["message"]
                if choice.get("finish_reason") == "tool_calls" and message.get("tool_calls"):
                    messages.append(message)
                    for tool_call in message["tool_calls"]:
                        fn = tool_call["function"]
                        name = fn["name"]
                        try:
                            arguments = json.loads(fn.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            arguments = {}
                        result_text = await self._call_tool(client, name, arguments)
                        sources.append(ChatSource(tool=name, result=result_text))
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result_text,
                            }
                        )
                    continue

                answer = (message.get("content") or "").strip()
                return ChatResponse(answer=answer, sources=sources)

        return ChatResponse(
            answer="Lo siento, no pude completar la consulta.",
            sources=sources,
        )

    async def _load_tools(self, client: httpx.AsyncClient) -> list[dict]:
        if self._tools_cache is not None:
            return self._tools_cache

        headers = (
            {"Authorization": f"Bearer {self.proxy_key}"} if self.proxy_key else None
        )
        try:
            response = await client.get(f"{self.proxy_url}/openapi.json", headers=headers)
        except httpx.TimeoutException:
            _log.error(
                "Timeout al obtener el spec del proxy de herramientas en %s",
                self.proxy_url,
            )
            raise AiBridgeException(
                "El proxy de herramientas (mcpo) no respondió a tiempo."
            )
        except httpx.HTTPError as e:
            _log.error(
                "No se pudo conectar con el proxy de herramientas en %s: %s",
                self.proxy_url,
                e,
            )
            raise AiBridgeException(
                f"No se pudo conectar con el proxy de herramientas en "
                f"{self.proxy_url}: {e}. Ejecuta ./iniciar.sh en asistente-bd."
            )
        if response.status_code >= 400:
            _log.error(
                "No se pudo obtener el spec del proxy: %s %s",
                response.status_code,
                response.text[:300],
            )
            raise AiBridgeException(
                "El proxy de herramientas (mcpo) no está disponible. "
                "Ejecuta ./iniciar.sh en asistente-bd."
            )

        spec = response.json()
        schemas = spec.get("components", {}).get("schemas", {})
        tools: list[dict] = []
        for path, methods in spec.get("paths", {}).items():
            operation = (methods or {}).get("post")
            if not operation:
                continue
            name = path.lstrip("/")
            description = operation.get("description") or operation.get("summary") or name
            parameters: dict = {"type": "object", "properties": {}}
            request_body = operation.get("requestBody")
            if request_body:
                schema = request_body["content"]["application/json"]["schema"]
                ref = schema.get("$ref")
                if ref:
                    model_name = ref.rsplit("/", 1)[-1]
                    model = schemas.get(model_name, {})
                    parameters = {
                        "type": "object",
                        "properties": model.get("properties", {}),
                        "required": model.get("required", []),
                    }
                else:
                    parameters = schema
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": parameters,
                    },
                }
            )

        self._tools_cache = tools
        return tools

    async def _call_tool(
        self, client: httpx.AsyncClient, name: str, arguments: dict
    ) -> str:
        headers = (
            {"Authorization": f"Bearer {self.proxy_key}"} if self.proxy_key else None
        )
        body = arguments or {}
        try:
            response = await client.post(
                f"{self.proxy_url}/{name}",
                json=body,
                headers=headers,
            )
        except httpx.TimeoutException:
            _log.error(
                "Timeout al llamar a la herramienta %s en %s", name, self.proxy_url
            )
            raise AiBridgeException(
                f"La herramienta {name} tardó demasiado en responder."
            )
        except httpx.HTTPError as e:
            _log.error(
                "No se pudo conectar con la herramienta %s en %s: %s",
                name,
                self.proxy_url,
                e,
            )
            raise AiBridgeException(
                f"No se pudo conectar con la herramienta {name} en "
                f"{self.proxy_url}: {e}"
            )
        if response.status_code >= 400:
            _log.error(
                "Tool %s respondió %s: %s",
                name,
                response.status_code,
                response.text[:300],
            )
            raise AiBridgeException(f"La herramienta {name} falló al consultar la base.")
        return response.text
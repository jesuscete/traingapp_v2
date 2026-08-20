"""Cliente HTTP del evaluador de rutinas (ai-parser).

Punto único desacoplado hacia el proveedor de IA: cambiar de modelo o de servicio
requiere tocar solo este módulo, igual que `app.core.parser.fetch_draft`.
"""

import httpx

from app.core.config import settings


async def fetch_routine_review(
    routine_name: str, payload: list[dict[str, object]]
) -> dict[str, object]:
    # La generación del LLM local puede tardar varios minutos en CPU: el timeout
    # debe cubrir el del proveedor (ai-parser, 600s) o el gateway corta con 502.
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(
            f"{settings.ai_parser_url.rstrip('/')}/analyze/routine",
            json={"routineName": routine_name, "payload": payload},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
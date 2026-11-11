"""Cliente HTTP del evaluador de rutinas (ai-parser).

Punto único desacoplado hacia el proveedor de IA: cambiar de modelo o de servicio
requiere tocar solo este módulo, igual que `app.core.parser.fetch_draft`.
"""

from app.core.ai_parser_http import ai_parser_client


async def fetch_routine_review(
    routine_name: str, payload: list[dict[str, object]]
) -> dict[str, object]:
    async with ai_parser_client() as client:
        response = await client.post(
            "/analyze/routine",
            json={"routineName": routine_name, "payload": payload},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
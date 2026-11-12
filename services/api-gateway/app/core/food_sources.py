"""Clientes de bases de alimentos externas (M5): Open Food Facts y USDA FoodData Central.

- Open Food Facts (ODbL): productos de marca y código de barras; subdominio español.
- USDA FDC (CC0): alimentos genéricos con macros fiables (en inglés).
Devuelven candidatos normalizados por 100 g; la caché local la gestiona el servicio.
"""

from dataclasses import dataclass, field

import httpx

from app.core.config import settings

USER_AGENT = "TrainingApp/0.1 (uso personal; https://github.com/jesuscete/traingapp_v2)"
OFF_FIELDS = (
    "code,product_name,product_name_es,generic_name_es,brands,nutriments,serving_size,"
    "serving_quantity"
)
USDA_NUTRIENTS = {
    "208": "kcal",
    "203": "protein",
    "205": "carbs",
    "204": "fat",
    "291": "fiber",
    "269": "sugar",
}


class FoodSourceError(Exception):
    """La fuente externa no respondió o devolvió datos inválidos."""


@dataclass(frozen=True)
class FoodCandidate:
    source: str  # off | usda
    external_id: str
    name: str
    kcal_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    fiber_100g: float | None = None
    sugar_100g: float | None = None
    brand: str | None = None
    barcode: str | None = None
    servings: list[dict[str, object]] = field(default_factory=list)


def _num(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return number if number >= 0 else None


def parse_off_product(product: dict[str, object]) -> FoodCandidate | None:
    """Producto OFF -> candidato; None si no trae kcal por 100 g (inservible para contar)."""
    nutriments = product.get("nutriments")
    if not isinstance(nutriments, dict):
        return None
    kcal = _num(nutriments.get("energy-kcal_100g"))
    if kcal is None:
        kj = _num(nutriments.get("energy_100g"))
        kcal = round(kj / 4.184, 1) if kj is not None else None
    name = next(
        (
            str(product[k]).strip()
            for k in ("product_name_es", "product_name", "generic_name_es")
            if isinstance(product.get(k), str) and str(product[k]).strip()
        ),
        None,
    )
    code = str(product.get("code") or "").strip()
    if kcal is None or not name or not code:
        return None
    servings: list[dict[str, object]] = []
    quantity = _num(product.get("serving_quantity"))
    if quantity:
        servings.append(
            {"label": str(product.get("serving_size") or "1 ración"), "grams": quantity}
        )
    brands = product.get("brands")
    return FoodCandidate(
        source="off",
        external_id=code,
        barcode=code,
        name=name[:200],
        brand=str(brands).split(",")[0].strip()[:120]
        if isinstance(brands, str) and brands
        else None,
        kcal_100g=kcal,
        protein_100g=_num(nutriments.get("proteins_100g")) or 0.0,
        carbs_100g=_num(nutriments.get("carbohydrates_100g")) or 0.0,
        fat_100g=_num(nutriments.get("fat_100g")) or 0.0,
        fiber_100g=_num(nutriments.get("fiber_100g")),
        sugar_100g=_num(nutriments.get("sugars_100g")),
        servings=servings,
    )


def parse_usda_food(food: dict[str, object]) -> FoodCandidate | None:
    values: dict[str, float] = {}
    nutrients = food.get("foodNutrients")
    for item in nutrients if isinstance(nutrients, list) else []:
        if not isinstance(item, dict):
            continue
        key = USDA_NUTRIENTS.get(str(item.get("nutrientNumber")))
        number = _num(item.get("value"))
        if key and number is not None:
            values.setdefault(key, number)
    if "kcal" not in values or not food.get("fdcId") or not food.get("description"):
        return None
    return FoodCandidate(
        source="usda",
        external_id=str(food["fdcId"]),
        name=str(food["description"])[:200],
        kcal_100g=values["kcal"],
        protein_100g=values.get("protein", 0.0),
        carbs_100g=values.get("carbs", 0.0),
        fat_100g=values.get("fat", 0.0),
        fiber_100g=values.get("fiber"),
        sugar_100g=values.get("sugar"),
    )


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.food_api_timeout_seconds, headers={"User-Agent": USER_AGENT}
    )


async def off_by_barcode(barcode: str) -> FoodCandidate | None:
    url = f"{settings.off_base_url.rstrip('/')}/api/v2/product/{barcode}.json"
    try:
        async with _client() as client:
            response = await client.get(url, params={"fields": OFF_FIELDS})
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodSourceError(f"Open Food Facts: {exc}") from exc
    product = data.get("product") if isinstance(data, dict) else None
    return parse_off_product(product) if isinstance(product, dict) else None


async def off_search(query: str, limit: int = 12) -> list[FoodCandidate]:
    url = f"{settings.off_base_url.rstrip('/')}/cgi/search.pl"
    params: dict[str, str | int] = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": OFF_FIELDS,
    }
    try:
        async with _client() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodSourceError(f"Open Food Facts: {exc}") from exc
    products = data.get("products") if isinstance(data, dict) else None
    found = [parse_off_product(p) for p in products or [] if isinstance(p, dict)]
    return [c for c in found if c is not None]


async def usda_search(query: str, limit: int = 5) -> list[FoodCandidate]:
    url = f"{settings.usda_base_url.rstrip('/')}/foods/search"
    params: dict[str, str | int] = {
        "query": query,
        "pageSize": limit,
        "dataType": "Foundation,SR Legacy",
        "api_key": settings.usda_api_key,
    }
    try:
        async with _client() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodSourceError(f"USDA: {exc}") from exc
    foods = data.get("foods") if isinstance(data, dict) else None
    found = [parse_usda_food(f) for f in foods or [] if isinstance(f, dict)]
    return [c for c in found if c is not None]

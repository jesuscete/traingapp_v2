"""Importacion puntual de productos de un supermercado o una marca desde Open Food Facts.

Usa el buscador search-a-licious de OFF (filtros por tienda y pais) y guarda los
productos como cache compartida (`source="off"`; `store=<tienda>` si es por tienda). Es idempotente:
la clave (source, external_id) evita duplicados, asi que relanzar es seguro.
Los alimentos propios de los usuarios no se tocan (tienen otro `source`).
"""

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Literal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.food_sources import (
    OFF_FIELDS,
    USER_AGENT,
    FoodCandidate,
    FoodSourceError,
    parse_off_product,
    product_brands,
)
from app.models import Food

logger = logging.getLogger(__name__)

MAX_KCAL_100G = 900.0  # el aceite puro ronda 900 kcal/100 g
MAX_MACROS_100G = 105.0  # margen de redondeo de las etiquetas
KCAL_TOLERANCE_ABS = 60.0
KCAL_TOLERANCE_REL = 0.35


@dataclass
class ImportStats:
    fetched: int = 0
    no_data: int = 0
    implausible: int = 0
    inserted: int = 0
    tagged: int = 0
    unchanged: int = 0
    rejected_examples: list[str] = field(default_factory=list)


def implausible_reason(cand: FoodCandidate) -> str | None:
    """Motivo por el que unos valores nutricionales no son creibles; None si son validos."""
    macros = cand.protein_100g + cand.carbs_100g + cand.fat_100g
    if cand.kcal_100g > MAX_KCAL_100G:
        return f"{cand.kcal_100g:.0f} kcal/100 g"
    if max(cand.protein_100g, cand.carbs_100g, cand.fat_100g) > 100 or macros > MAX_MACROS_100G:
        return f"macros suman {macros:.0f} g/100 g"
    if macros == 0:
        # Sin macros solo es creible si tampoco hay energia (agua, cafe, infusiones).
        return None if cand.kcal_100g <= 5 else "kcal sin macros"
    expected = 4 * cand.protein_100g + 4 * cand.carbs_100g + 9 * cand.fat_100g
    tolerance = max(KCAL_TOLERANCE_ABS, KCAL_TOLERANCE_REL * cand.kcal_100g)
    if abs(expected - cand.kcal_100g) > tolerance:
        return f"kcal {cand.kcal_100g:.0f} vs macros {expected:.0f}"
    return None


@dataclass(frozen=True)
class ImportSource:
    """Que importar: una tienda (stores) o una marca (brands_tags) vendida en un pais."""

    kind: Literal["store", "brand"]
    value: str
    label: str
    country: str = "spain"

    def query(self) -> str:
        country = f'countries_tags:"en:{self.country.lower()}"'
        if self.kind == "store":
            return f'stores:"{self.value.lower()}" AND {country}'
        # Etiqueta exacta: "big" no arrastra "Big D" ni "Big Man".
        slug = re.sub(r"[^a-z0-9]+", "-", self.value.lower()).strip("-")
        return f'brands_tags:"{slug}" AND {country}'


async def fetch_page(
    client: httpx.AsyncClient, query: str, page: int, page_size: int
) -> tuple[list[dict[str, object]], int]:
    """Una pagina de resultados. Devuelve (productos, total de paginas)."""
    url = f"{settings.off_search_url.rstrip('/')}/search"
    params: dict[str, str | int] = {
        "q": query,
        "page": page,
        "page_size": page_size,
        "fields": OFF_FIELDS,
    }
    try:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FoodSourceError(f"Open Food Facts (pagina {page}): {exc}") from exc
    if not isinstance(data, dict):
        raise FoodSourceError(f"Open Food Facts (pagina {page}): respuesta inesperada")
    hits = data.get("hits")
    page_count = data.get("page_count")
    products = [h for h in hits if isinstance(h, dict)] if isinstance(hits, list) else []
    return products, page_count if isinstance(page_count, int) else 0


async def fetch_products(
    source: ImportSource,
    page_size: int = 100,
    max_pages: int | None = None,
    pause_seconds: float = 1.0,
    on_page: Callable[[int, int], None] | None = None,
) -> list[dict[str, object]]:
    """Todas las paginas de la fuente, con pausa entre peticiones para no saturar OFF."""
    products: list[dict[str, object]] = []
    page, total = 1, 1
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": USER_AGENT}) as client:
        while page <= total and (max_pages is None or page <= max_pages):
            batch, total = await fetch_page(client, source.query(), page, page_size)
            products.extend(batch)
            if on_page is not None:
                on_page(page, total)
            if not batch:
                break
            page += 1
            if page <= total:
                await asyncio.sleep(pause_seconds)
    return products


def clean_brand(brand: str | None, store_label: str | None) -> str | None:
    """Quita el nombre del súper pegado a la marca: "AlestoLidl"/"Tastino (Lidl)" -> marca."""
    if not brand:
        return None
    text = brand
    if store_label:
        text = re.sub(re.escape(store_label), " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[()]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -,./|")
    return text[:120] or None


def _brand_for(product: dict[str, object], cand: FoodCandidate, source: ImportSource) -> str | None:
    if source.kind == "brand":
        return source.label[:120]
    # La marca "Lidl" ya va en store: mejor la submarca (Milbona, Fin Carré...) si la hay.
    brands = [clean_brand(b, source.label) for b in product_brands(product)]
    return next((b for b in brands if b), None)


def select_candidates(
    products: list[dict[str, object]], source: ImportSource, stats: ImportStats
) -> list[FoodCandidate]:
    """Productos OFF -> candidatos validos (con kcal y valores creibles), sin duplicados."""
    store = source.label if source.kind == "store" else None
    out: dict[str, FoodCandidate] = {}
    for product in products:
        stats.fetched += 1
        cand = parse_off_product(product)
        if cand is None:
            stats.no_data += 1
            continue
        reason = implausible_reason(cand)
        if reason is not None:
            stats.implausible += 1
            if len(stats.rejected_examples) < 10:
                stats.rejected_examples.append(f"{cand.name} ({reason})")
            continue
        brand = _brand_for(product, cand, source)
        out[cand.external_id] = replace(cand, store=store, brand=brand)
    return list(out.values())


async def save_candidates(
    session: AsyncSession, candidates: list[FoodCandidate], stats: ImportStats
) -> None:
    """Inserta los nuevos y etiqueta con la tienda los que ya estaban en cache."""
    ids = [c.external_id for c in candidates]
    existing: dict[str, Food] = {}
    for chunk_start in range(0, len(ids), 500):
        chunk = ids[chunk_start : chunk_start + 500]
        rows = await session.scalars(
            select(Food).where(Food.source == "off", Food.external_id.in_(chunk))
        )
        existing.update({row.external_id: row for row in rows if row.external_id})
    for cand in candidates:
        food = existing.get(cand.external_id)
        if food is None:
            session.add(
                Food(
                    source=cand.source,
                    external_id=cand.external_id,
                    barcode=cand.barcode,
                    name=cand.name,
                    brand=cand.brand,
                    store=cand.store,
                    kcal_100g=cand.kcal_100g,
                    protein_100g=cand.protein_100g,
                    carbs_100g=cand.carbs_100g,
                    fat_100g=cand.fat_100g,
                    fiber_100g=cand.fiber_100g,
                    sugar_100g=cand.sugar_100g,
                    servings=cand.servings,
                )
            )
            stats.inserted += 1
        elif food.store is None and cand.store is not None:
            food.store = cand.store
            stats.tagged += 1
        else:
            stats.unchanged += 1
    await session.commit()

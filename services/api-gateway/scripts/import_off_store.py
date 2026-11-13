"""Importa una vez productos de supermercados o marcas desde Open Food Facts.

Rellena la tabla `food` con los productos vendidos en el pais indicado (solo alimentos:
OFF no tiene bazar). Es idempotente: relanzarlo no duplica nada.

Cada --store/--brand admite "valor" o "valor:Etiqueta" (la etiqueta es lo que se ve
en la app; por defecto el valor con mayusculas iniciales).

Uso (desde services/api-gateway):
    .venv/Scripts/python.exe -m scripts.import_off_store --store lidl --dry-run
    .venv/Scripts/python.exe -m scripts.import_off_store --store mercadona --store carrefour
    .venv/Scripts/python.exe -m scripts.import_off_store --brand prozis --brand hsn:HSN
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Literal

from app.core.database import async_session_factory, engine
from app.core.food_sources import FoodSourceError
from app.services.food_import import (
    ImportSource,
    ImportStats,
    fetch_products,
    save_candidates,
    select_candidates,
)


def _source(kind: Literal["store", "brand"], raw: str, country: str) -> ImportSource:
    value, _, label = raw.partition(":")
    value = value.strip()
    return ImportSource(kind, value, label.strip() or value.title(), country)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", action="append", default=[], help="supermercado (repetible)")
    parser.add_argument("--brand", action="append", default=[], help="marca (repetible)")
    parser.add_argument("--country", default="spain", help="pais en OFF (por defecto: spain)")
    parser.add_argument("--dry-run", action="store_true", help="solo contar, sin escribir")
    parser.add_argument("--max-pages", type=int, default=None, help="limitar paginas (pruebas)")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--pause", type=float, default=1.0, help="segundos entre peticiones")
    args = parser.parse_args()
    if not args.store and not args.brand:
        parser.error("indica al menos un --store o un --brand")
    return args


async def _import_one(source: ImportSource, args: argparse.Namespace) -> bool:
    kind = "tienda" if source.kind == "store" else "marca"
    print(f"\n=== {source.label} ({kind}, {source.country}) ===")
    try:
        products = await fetch_products(
            source,
            page_size=args.page_size,
            max_pages=args.max_pages,
            pause_seconds=args.pause,
            on_page=lambda page, total: print(f"  página {page}/{total}", flush=True),
        )
    except FoodSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return False

    stats = ImportStats()
    candidates = select_candidates(products, source, stats)
    print(
        f"Descargados: {stats.fetched} · sin kcal/nombre: {stats.no_data} · "
        f"valores dudosos: {stats.implausible} · válidos: {len(candidates)}"
    )
    if stats.rejected_examples:
        print("Ejemplos descartados por valores dudosos:")
        for example in stats.rejected_examples[:5]:
            print(f"  - {example}")

    if args.dry_run:
        print("Ejemplos válidos:")
        for cand in candidates[:5]:
            print(
                f"  - {cand.name} [{cand.brand or '-'}] {cand.kcal_100g:.0f} kcal · "
                f"P {cand.protein_100g:g} H {cand.carbs_100g:g} G {cand.fat_100g:g}"
            )
        return True

    async with async_session_factory() as session:
        await save_candidates(session, candidates, stats)
    print(
        f"Guardado. Nuevos: {stats.inserted} · ya existían y se etiquetaron: {stats.tagged} · "
        f"sin cambios: {stats.unchanged}"
    )
    return True


async def _main(args: argparse.Namespace) -> int:
    engine.echo = False  # el log SQL de desarrollo taparía el resumen
    sources = [_source("store", s, args.country) for s in args.store] + [
        _source("brand", b, args.country) for b in args.brand
    ]
    ok = True
    for index, source in enumerate(sources):
        if index > 0:
            await asyncio.sleep(args.pause)
        ok = await _import_one(source, args) and ok
    if args.dry_run:
        print("\n--dry-run: no se ha escrito nada.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_main(_parse_args())))

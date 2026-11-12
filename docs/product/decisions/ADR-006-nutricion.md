# ADR-006 · Nutrición: fuentes, registro exacto o estimado y cálculo de objetivos

**Estado:** Aceptada · 2026-11-12 · Hito M5 ([análisis §6](../ANALISIS_TECNICO.md))

## Decisión
- **Fuentes:**
  - Open Food Facts (subdominio español; productos de marca y código de barras).
  - USDA FoodData Central (genéricos).
  - Los alimentos propios del usuario.
  - Todo lo consultado se guarda en la caché local `food` (por 100 g + raciones).
- **Dos formas de registrar,** guardando siempre el método en `meal_entry.method`:
  - **Exactas:** `pesada` (gramos de báscula) y `etiqueta` (alimento propio con los valores del envase).
  - **Estimadas:** `racion`, `rapida` (kcal sueltas) e `ia` (texto libre).
  - El resumen del día separa las kcal exactas de las estimadas: clave en un corte de peso.
- **Texto libre:**
  - Claude (ai-parser `/parse/meal`) separa los alimentos y estima gramos y valores por 100 g, junto con el nombre en inglés.
  - El gateway contrasta cada alimento en este orden: **alimento propio > USDA > estimación de Claude**.
  - Un resultado de USDA solo se acepta si sus kcal/100 g son **plausibles** frente a la estimación (ratio 0,6-1,6 o ±60 kcal), eligiendo el más cercano entre 5 candidatos. Motivo: en la prueba real, "coffee with milk" devolvía café soluble en polvo (549 kcal/100 g → 1.098 kcal en un café).
  - Nada se guarda hasta que el usuario revisa y confirma.
- **Copia de macros** en cada comida: el historial no cambia si se corrige el alimento.
- **Objetivo diario** (`analytics/nutrition.py`, determinista):
  - Mifflin-St Jeor × actividad cotidiana sin entrenos (1,4 por defecto), más las **kcal reales de los entrenos del día**.
  - Ajuste según el objetivo: perder −0,5 kg/semana; ganar +0,25; corte calculado con el peso y la fecha objetivo.
  - Límites: máximo 1 % del peso por semana, déficit ≤25 % del mantenimiento y nunca por debajo del basal.
  - Macros: proteína en g/kg (2,0 por defecto); grasa ≥0,8 g/kg y ≥20 % de las kcal; resto en hidratos.
- **Peso corporal** con media móvil de 7 días; el último peso actualiza el perfil.
- **Agente:** `ver_nutricion` y `registrar_comida`; esta última propone y el usuario confirma.

## Consecuencias
- ✅ Precisión cuando se pesa y comodidad cuando no, siempre sabiendo qué es estimado.
- ⚠️ USDA con `DEMO_KEY` tiene un límite muy bajo: conviene una clave gratuita propia (`APP_USDA_API_KEY`, se pide en https://fdc.nal.usda.gov/api-key-signup).
- ⚠️ La calidad de Open Food Facts varía según el producto (colaborativa). Un producto mal descrito se corrige creando un alimento propio desde la etiqueta.
- ⚠️ El escáner de código de barras necesita HTTPS en el móvil (mkcert, `dev-up.ps1 -Https`); mientras tanto, el código se teclea.

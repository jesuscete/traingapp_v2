# web: frontend de TrainingApp

Next.js 16 (App Router) + React 19 + TypeScript strict. Consume la API de `services/api-gateway`.

## Arranque

Lo normal es arrancar todo con `scripts/dev-up.ps1` desde la raíz. Para la web sola:

```powershell
E:\nodejs\npx.cmd next dev            # http://localhost:3000
E:\nodejs\node.exe node_modules\typescript\bin\tsc --noEmit   # verificación de tipos
```

## Configuración

| Variable | Por defecto | Uso |
| :-- | :-- | :-- |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | URL del api-gateway |

### Usarla desde el móvil (misma red local)
1. `next dev -H 0.0.0.0` y `NEXT_PUBLIC_API_URL=http://<IP-del-PC>:8000`.
2. En el gateway: `APP_CORS_ORIGINS=http://localhost:3000,http://<IP-del-PC>:3000` y uvicorn con `--host 0.0.0.0`.

## Estructura
- `app/`: rutas (dashboard, entrenar, entrenos, fatiga, rutinas, analisis, chat, perfil).
- `components/`: UI (BodyMap, gráficos SVG, chat, rutinas).
- `lib/`: cliente de API (`api.ts`), tipos y utilidades.

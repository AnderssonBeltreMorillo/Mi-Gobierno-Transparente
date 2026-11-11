# Frontend — Mi Gobierno Transparente

Dashboard en React + TypeScript + Vite + Tailwind CSS + Lucide Icons para el
monitor automático de compras públicas.

## Requisitos

- Node.js 20+
- Backend FastAPI corriendo en `http://localhost:8000`

## Desarrollo

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`.

## Build

```powershell
npm run build
```

## Configuración

La URL de la API se puede cambiar con `VITE_API_URL`:

```powershell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

Por defecto usa `http://localhost:8000`, que ya está permitido por el
`CORSMiddleware` del backend para `http://localhost:5173`.

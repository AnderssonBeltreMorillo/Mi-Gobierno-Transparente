import type { ReactNode } from "react";
import { Loader2, RefreshCw, WifiOff } from "lucide-react";
import { API_URL } from "../lib/api";

function Marco({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-canvas">
      <div
        aria-hidden="true"
        className="surface-grid pointer-events-none absolute inset-0 -z-10 opacity-50"
      />
      <div className="tricolor h-1 w-full" />
      <div className="mx-auto flex min-h-[calc(100vh-4px)] max-w-7xl items-center justify-center px-4 py-10">
        {children}
      </div>
    </div>
  );
}

export function EstadoCarga() {
  return (
    <Marco>
      <div className="flex flex-col items-center text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-ultramar text-white shadow-lg shadow-ultramar/20">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
        </div>
        <p className="mt-4 text-base font-extrabold text-slate-900">
          Consultando la API de transparencia…
        </p>
        <p className="mt-1 text-sm text-slate-500">Conectando con {API_URL}</p>
      </div>
    </Marco>
  );
}

interface PropsError {
  mensaje: string;
  onReintentar: () => void;
}

export function EstadoError({ mensaje, onReintentar }: PropsError) {
  return (
    <Marco>
      <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-xl shadow-slate-200/50 sm:p-8">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-red-50 text-bermellon">
          <WifiOff className="h-6 w-6" aria-hidden="true" />
        </div>
        <h1 className="mt-4 text-xl font-black tracking-tight text-slate-950">
          No se pudo consultar la API
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">{mensaje}</p>
        <p className="mt-3 overflow-x-auto rounded-xl bg-slate-50 p-3 font-mono text-xs text-slate-500">
          {API_URL}
        </p>
        <button
          type="button"
          onClick={onReintentar}
          className="mt-5 inline-flex items-center gap-2 rounded-full bg-ultramar px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-ultramar/90 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ultramar/20"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Reintentar conexión
        </button>
        <p className="mt-4 text-xs leading-5 text-slate-400">
          Asegúrate de que el backend esté corriendo:
          <br />
          <code className="rounded bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-500">
            uvicorn mi_gobierno_transparente.presentation.app:app --reload
          </code>
        </p>
      </div>
    </Marco>
  );
}

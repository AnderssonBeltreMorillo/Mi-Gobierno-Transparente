import { Landmark, RefreshCw } from "lucide-react";

interface Props {
  cargando: boolean;
  onRefresh: () => void;
}

export function Header({ cargando, onRefresh }: Props) {
  return (
    <header className="sticky top-0 z-40">
      <div className="tricolor h-1 w-full" />
      <div className="border-b border-slate-200/80 bg-white/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
          <div className="flex items-center gap-3">
            <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-ultramar text-white shadow-lg shadow-ultramar/20">
              <Landmark
                className="h-5 w-5"
                strokeWidth={1.8}
                aria-hidden="true"
              />
              <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-bermellon ring-2 ring-white" />
            </div>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-ultramar/60">
                República Dominicana
              </p>
              <h1 className="mt-0.5 text-sm font-extrabold leading-tight tracking-tight text-slate-900 sm:text-base lg:text-lg">
                Mi Gobierno Transparente
                <span className="mx-1 hidden text-slate-300 sm:inline">—</span>
                <span className="block text-xs font-semibold text-slate-500 sm:inline sm:text-sm">
                  Monitor Automático de Compras Públicas
                </span>
              </h1>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-bold text-emerald-700 sm:text-xs">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              Scraper DGCP &amp; Supermercados: Activo
            </span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium text-slate-500 sm:text-xs">
              Demo: Adquisición de Alimentos y Aseo
            </span>
            <button
              type="button"
              onClick={onRefresh}
              disabled={cargando}
              className="inline-flex items-center gap-1.5 rounded-full border border-ultramar/15 bg-ultramar px-3 py-1.5 text-[11px] font-bold text-white shadow-sm transition hover:bg-ultramar/90 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ultramar/20 disabled:cursor-not-allowed disabled:opacity-60 sm:text-xs"
            >
              <RefreshCw
                className={`h-3.5 w-3.5 ${cargando ? "animate-spin" : ""}`}
                aria-hidden="true"
              />
              {cargando ? "Actualizando" : "Actualizar"}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}

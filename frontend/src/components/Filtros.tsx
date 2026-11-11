import { Search } from "lucide-react";
import type { ConteosRiesgo, FiltroRiesgo } from "../types";

interface OpcionFiltro {
  valor: FiltroRiesgo;
  etiqueta: string;
  activo: string;
}

const OPCIONES: OpcionFiltro[] = [
  {
    valor: "todos",
    etiqueta: "Todos",
    activo: "border-ultramar bg-ultramar text-white",
  },
  {
    valor: "precio_justo",
    etiqueta: "Justos",
    activo: "border-emerald-600 bg-emerald-600 text-white",
  },
  {
    valor: "alerta_amarilla",
    etiqueta: "Irregulares",
    activo: "border-amber-400 bg-amber-400 text-slate-950",
  },
  {
    valor: "alto_riesgo",
    etiqueta: "Sobrevalorados",
    activo: "border-bermellon bg-bermellon text-white",
  },
];

interface Props {
  filtro: FiltroRiesgo;
  onCambiarFiltro: (filtro: FiltroRiesgo) => void;
  busqueda: string;
  onCambiarBusqueda: (valor: string) => void;
  conteos: ConteosRiesgo;
}

export function Filtros({
  filtro,
  onCambiarFiltro,
  busqueda,
  onCambiarBusqueda,
  conteos,
}: Props) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div
        className="flex flex-wrap items-center gap-2"
        role="group"
        aria-label="Filtrar por nivel de riesgo"
      >
        {OPCIONES.map((opcion) => {
          const activo = filtro === opcion.valor;
          return (
            <button
              key={opcion.valor}
              type="button"
              onClick={() => onCambiarFiltro(opcion.valor)}
              aria-pressed={activo}
              className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-bold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-ultramar/10 ${
                activo
                  ? opcion.activo
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              {opcion.etiqueta}
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] tabular-nums ${
                  activo
                    ? "bg-white/20 text-inherit"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {conteos[opcion.valor]}
              </span>
            </button>
          );
        })}
      </div>

      <div className="relative w-full sm:w-64">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        />
        <input
          type="search"
          value={busqueda}
          onChange={(evento) => onCambiarBusqueda(evento.target.value)}
          placeholder="Buscar producto o marca..."
          aria-label="Buscar producto o marca"
          className="w-full rounded-full border border-slate-200 bg-white py-2 pl-9 pr-4 text-sm text-slate-700 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-ultramar/40 focus:ring-4 focus:ring-ultramar/10"
        />
      </div>
    </div>
  );
}

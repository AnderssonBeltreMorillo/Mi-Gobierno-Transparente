import {
  AlertTriangle,
  CheckCircle2,
  ScanSearch,
  TrendingUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ResumenRiesgo } from "../types";
import { formatearPorcentaje } from "../lib/formato";

type Tono = "azul" | "verde" | "ambar" | "rojo";

interface Tonos {
  icono: string;
  barra: string;
  valor: string;
}

const TONOS: Record<Tono, Tonos> = {
  azul: {
    icono: "bg-ultramar/10 text-ultramar",
    barra: "bg-ultramar",
    valor: "text-slate-950",
  },
  verde: {
    icono: "bg-emerald-50 text-emerald-600",
    barra: "bg-emerald-500",
    valor: "text-emerald-700",
  },
  ambar: {
    icono: "bg-amber-50 text-amber-600",
    barra: "bg-amber-400",
    valor: "text-amber-700",
  },
  rojo: {
    icono: "bg-red-50 text-bermellon",
    barra: "bg-bermellon",
    valor: "text-bermellon",
  },
};

interface PropsKpi {
  titulo: string;
  valor: number;
  detalle: string;
  icono: LucideIcon;
  tono: Tono;
  extra?: string;
}

function Kpi({ titulo, valor, detalle, icono: Icono, tono, extra }: PropsKpi) {
  const estilos = TONOS[tono];

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-slate-200/60">
      <span
        className={`absolute inset-x-0 top-0 h-0.5 ${estilos.barra}`}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-3">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${estilos.icono}`}
        >
          <Icono className="h-5 w-5" aria-hidden="true" />
        </div>
        {extra ? (
          <span className="rounded-full bg-red-50 px-2 py-1 text-[10px] font-bold text-bermellon ring-1 ring-inset ring-red-100">
            {extra}
          </span>
        ) : null}
      </div>
      <p className="mt-4 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">
        {titulo}
      </p>
      <p
        className={`mt-1 text-3xl font-black tracking-tight tabular-nums ${estilos.valor}`}
      >
        {valor}
      </p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{detalle}</p>
    </article>
  );
}

interface Props {
  resumen: ResumenRiesgo;
}

export function ResumenKpis({ resumen }: Props) {
  return (
    <section
      aria-label="Resumen de riesgo"
      className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
    >
      <Kpi
        titulo="Total analizadas"
        valor={resumen.total_evaluaciones}
        detalle="Evaluaciones procesadas por el monitor automático."
        icono={ScanSearch}
        tono="azul"
      />
      <Kpi
        titulo="Justas"
        valor={resumen.precio_justo}
        detalle="Precio igual o por debajo del mercado."
        icono={CheckCircle2}
        tono="verde"
      />
      <Kpi
        titulo="Irregulares"
        valor={resumen.alerta_amarilla}
        detalle="Sobreprecio entre 1 % y 15 % sobre el mercado."
        icono={AlertTriangle}
        tono="ambar"
      />
      <Kpi
        titulo="Sobrevaloradas"
        valor={resumen.alto_riesgo}
        detalle="Sobreprecio superior al 15 % sobre el mercado."
        icono={TrendingUp}
        tono="rojo"
        extra={`${formatearPorcentaje(resumen.porcentaje_alto_riesgo)} del total`}
      />
    </section>
  );
}

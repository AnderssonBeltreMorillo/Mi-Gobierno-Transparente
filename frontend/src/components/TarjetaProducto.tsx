import { ExternalLink, Package } from "lucide-react";
import type { Comparacion } from "../types";
import {
  aNumero,
  etiquetaCategoria,
  etiquetaUnidad,
  formatearMoneda,
  formatearPorcentaje,
} from "../lib/formato";
import { FUENTE_DGCP, obtenerFuenteMercado } from "../lib/fuentes";
import { EtiquetaRiesgo } from "./EtiquetaRiesgo";

interface Props {
  comparacion: Comparacion;
}

function colorBarra(nivel: Comparacion["evaluacion"]["nivel_riesgo"]): string {
  if (nivel === "alto_riesgo") {
    return "bg-bermellon";
  }
  if (nivel === "alerta_amarilla") {
    return "bg-amber-400";
  }
  return "bg-emerald-500";
}

export function TarjetaProducto({ comparacion }: Props) {
  const { producto, evaluacion } = comparacion;
  const excedente = aNumero(evaluacion.excedente);
  const sobreprecio = aNumero(evaluacion.sobreprecio_porcentaje);
  const mercado = obtenerFuenteMercado(producto.nombre);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ultramar/5 text-ultramar">
            <Package className="h-4 w-4" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold leading-5 text-slate-900">
              {producto.nombre}
            </p>
            <p className="mt-0.5 text-[11px] text-slate-500">
              {producto.marca ?? "Sin marca"} ·{" "}
              {etiquetaUnidad(producto.unidad_medida)} ·{" "}
              {etiquetaCategoria(producto.categoria)}
            </p>
          </div>
        </div>
        <div className="shrink-0">
          <EtiquetaRiesgo nivel={evaluacion.nivel_riesgo} compacta />
        </div>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-2.5">
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Precio licitado
          </dt>
          <dd className="mt-1 text-sm font-extrabold tabular-nums text-slate-900">
            {formatearMoneda(evaluacion.monto_reportado, evaluacion.moneda)}
          </dd>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Precio mercado
          </dt>
          <dd className="mt-1 text-sm font-extrabold tabular-nums text-slate-900">
            {formatearMoneda(evaluacion.monto_mercado, evaluacion.moneda)}
          </dd>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Diferencia
          </dt>
          <dd
            className={`mt-1 text-sm font-extrabold tabular-nums ${
              excedente > 0 ? "text-bermellon" : "text-slate-500"
            }`}
          >
            {excedente > 0 ? "+" : ""}
            {formatearMoneda(evaluacion.excedente, evaluacion.moneda)}
          </dd>
        </div>
        <div className="rounded-xl bg-slate-50 p-3">
          <dt className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
            Sobreprecio
          </dt>
          <dd className="mt-1 text-sm font-extrabold tabular-nums text-slate-900">
            {formatearPorcentaje(sobreprecio)}
          </dd>
        </div>
      </dl>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${colorBarra(evaluacion.nivel_riesgo)}`}
          style={{ width: `${Math.min(100, Math.max(0, sobreprecio))}%` }}
        />
      </div>

      <div className="mt-3 flex items-center justify-between gap-3 border-t border-slate-100 pt-3">
        <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">
          Fuentes verificables
        </span>
        <div className="flex items-center gap-3">
          <a
            href={FUENTE_DGCP.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-bold text-ultramar transition hover:text-bermellon hover:underline"
          >
            DGCP
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
          <a
            href={mercado.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 transition hover:text-ultramar hover:underline"
          >
            {mercado.nombre}
            <ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        </div>
      </div>
    </article>
  );
}

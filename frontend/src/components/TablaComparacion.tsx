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
  comparaciones: Comparacion[];
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

export function TablaComparacion({ comparaciones }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] border-collapse text-left">
        <caption className="sr-only">
          Comparación de precios licitados contra precios de mercado por
          producto
        </caption>
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/90 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-500">
            <th scope="col" className="px-5 py-3.5">
              Producto
            </th>
            <th scope="col" className="px-4 py-3.5 text-right">
              Precio licitado
            </th>
            <th scope="col" className="px-4 py-3.5 text-right">
              Precio mercado
            </th>
            <th scope="col" className="px-4 py-3.5 text-right">
              Diferencia
            </th>
            <th scope="col" className="px-4 py-3.5">
              Sobreprecio
            </th>
            <th scope="col" className="px-4 py-3.5">
              Etiqueta
            </th>
            <th scope="col" className="px-5 py-3.5">
              Fuentes
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {comparaciones.map(({ producto, evaluacion }) => {
            const diferencia = aNumero(evaluacion.diferencia);
            const sobreprecio = aNumero(evaluacion.sobreprecio_porcentaje);
            const mercado = obtenerFuenteMercado(producto.nombre);

            return (
              <tr
                key={evaluacion.id}
                className="group transition hover:bg-slate-50/80"
              >
                <td className="px-5 py-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ultramar/5 text-ultramar">
                      <Package className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900">
                        {producto.nombre}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-500">
                        {producto.marca ?? "Sin marca"} ·{" "}
                        {etiquetaUnidad(producto.unidad_medida)} ·{" "}
                        {etiquetaCategoria(producto.categoria)}
                      </p>
                      {producto.descripcion ? <p className="mt-1 max-w-xs text-[10px] leading-4 text-slate-400">{producto.descripcion}</p> : null}
                    </div>
                  </div>
                </td>

                <td className="px-4 py-4 text-right text-sm font-bold tabular-nums text-slate-900">
                  {formatearMoneda(
                    evaluacion.monto_reportado,
                    evaluacion.moneda,
                  )}
                </td>

                <td className="px-4 py-4 text-right text-sm font-semibold tabular-nums text-slate-600">
                  {formatearMoneda(
                    evaluacion.monto_mercado,
                    evaluacion.moneda,
                  )}
                </td>

                <td
                  className={`px-4 py-4 text-right text-sm font-bold tabular-nums ${
                    diferencia > 0 ? "text-bermellon" : diferencia < 0 ? "text-emerald-600" : "text-slate-500"
                  }`}
                >
                  {diferencia > 0 ? "+" : ""}
                  {formatearMoneda(diferencia, evaluacion.moneda)}
                </td>

                <td className="px-4 py-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-sm font-extrabold tabular-nums ${
                        evaluacion.nivel_riesgo === "alto_riesgo"
                          ? "text-bermellon"
                          : evaluacion.nivel_riesgo === "alerta_amarilla"
                            ? "text-amber-600"
                            : "text-emerald-600"
                      }`}
                    >
                      {formatearPorcentaje(sobreprecio)}
                    </span>
                    <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                      <span
                        className={`block h-full rounded-full ${colorBarra(
                          evaluacion.nivel_riesgo,
                        )}`}
                        style={{
                          width: `${Math.min(100, Math.max(0, sobreprecio))}%`,
                        }}
                      />
                    </span>
                  </div>
                </td>

                <td className="px-4 py-4">
                  <EtiquetaRiesgo nivel={evaluacion.nivel_riesgo} />
                </td>

                <td className="px-5 py-4">
                  <div className="flex flex-col gap-1">
                    <a
                      href={FUENTE_DGCP.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex w-fit items-center gap-1 text-[11px] font-bold text-ultramar transition hover:text-bermellon hover:underline"
                    >
                      {FUENTE_DGCP.nombre}
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </a>
                    <a
                      href={mercado.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex w-fit items-center gap-1 text-[11px] font-semibold text-slate-500 transition hover:text-ultramar hover:underline"
                    >
                      {mercado.nombre}
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                    </a>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

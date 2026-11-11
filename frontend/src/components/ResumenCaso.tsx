import { AlertTriangle, CheckCircle2, Clock3, Landmark, Scale } from "lucide-react";
import type { Licitacion, ResumenRiesgo } from "../types";
import { formatearFecha, formatearPorcentaje } from "../lib/formato";
import { formatearRD } from "../lib/impactoFinanciero";
import { ImpactoFinancieroPanel } from "./ImpactoFinanciero";
import { MapaRD } from "./MapaRD";

interface Props {
  resumen: ResumenRiesgo;
  totalProductos: number;
  ultimaActualizacion: number;
  licitacion: Licitacion;
}

function porcentaje(cantidad: number, total: number): string {
  const valor = total ? cantidad * 100 / total : 0;
  return `${Number.isInteger(valor) ? valor.toFixed(0) : valor.toFixed(1)}%`;
}

function GraficoRiesgo({ resumen }: { resumen: ResumenRiesgo }) {
  const total = Math.max(resumen.total_evaluaciones, 1);
  const radio = 36;
  const circunferencia = 2 * Math.PI * radio;
  const segmentos = [
    { etiqueta: "Justas", valor: resumen.precio_justo, color: "#10B981" },
    { etiqueta: "Irregulares", valor: resumen.alerta_amarilla, color: "#F59E0B" },
    { etiqueta: "Sobrevaloradas", valor: resumen.alto_riesgo, color: "#CE1126" },
  ];
  let recorrido = 0;

  return <div className="relative flex items-center gap-4"><svg viewBox="0 0 100 100" role="img" aria-label="Gráfico circular de evaluación por nivel de riesgo" className="h-32 w-32 shrink-0"><circle cx="50" cy="50" r={radio} fill="none" stroke="rgba(255,255,255,0.13)" strokeWidth="16"/>{segmentos.map((segmento) => {
    const longitud = (segmento.valor / total) * circunferencia;
    const offset = recorrido;
    recorrido += longitud;
    return <circle key={segmento.etiqueta} cx="50" cy="50" r={radio} fill="none" stroke={segmento.color} strokeWidth="16" strokeDasharray={`${longitud} ${circunferencia - longitud}`} strokeDashoffset={-offset} transform="rotate(-90 50 50)"/>;
  })}<text x="50" y="48" textAnchor="middle" className="fill-white text-[17px] font-black">{resumen.total_evaluaciones}</text><text x="50" y="61" textAnchor="middle" className="fill-white/60 text-[6px] font-bold uppercase tracking-wider">artículos</text></svg><ul className="min-w-0 space-y-2 text-[11px]">{segmentos.map((segmento) => <li key={segmento.etiqueta} className="flex items-center gap-2"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: segmento.color }}/><span className="min-w-0 flex-1 text-white/75">{segmento.etiqueta}</span><strong className="whitespace-nowrap text-white">{segmento.valor} ({porcentaje(segmento.valor, resumen.total_evaluaciones)})</strong></li>)}</ul></div>;
}

export function ResumenCaso({ resumen, totalProductos, ultimaActualizacion, licitacion }: Props) {
  const globalJusta = licitacion.estado === "Justa";
  const montoTotal = Number(licitacion.monto_total) || 0;
  const montoNoEvaluable = Number(licitacion.monto_no_evaluable ?? "0") || 0;
  const montoEvaluable = montoTotal - montoNoEvaluable;
  const montoMercado = Number(licitacion.monto_mercado) || 0;
  const mostrarMontoEvaluable = montoEvaluable >= 0 && montoEvaluable < montoTotal;
  const detalleMonto = mostrarMontoEvaluable
    ? `${formatearRD(montoEvaluable)} evaluables (de ${formatearRD(montoTotal)} total) frente a ${formatearRD(montoMercado)} de mercado (${formatearPorcentaje(licitacion.sobreprecio)}).`
    : `${formatearRD(montoTotal)} licitados frente a ${formatearRD(montoMercado)} de mercado (${formatearPorcentaje(licitacion.sobreprecio)}).`;

  return <section className="animate-fade-up relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-[0_20px_60px_-35px_rgba(0,45,98,0.35)]"><div aria-hidden="true" className="hero-glow pointer-events-none absolute inset-0"/><div className="relative grid items-start gap-6 p-5 sm:p-7 md:grid-cols-2 lg:p-9">
    <div className="flex flex-col"><div className="flex flex-wrap items-center gap-2"><span className="inline-flex items-center gap-1.5 rounded-full border border-ultramar/15 bg-ultramar/5 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-ultramar"><Landmark className="h-3.5 w-3.5"/>Dictamen de versión</span><span className="text-xs font-medium text-slate-500">{licitacion.titulo}</span></div><h2 className="mt-4 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">Dictamen General del Caso</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Evaluación conjunta de viabilidad presupuestaria y riesgo individual por renglón para esta versión del expediente.</p>
      <div className="mt-5 space-y-3"><div className={`flex items-start gap-3 rounded-2xl border p-4 ${globalJusta ? "border-emerald-200 bg-emerald-50/80" : "border-amber-200 bg-amber-50"}`}><span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${globalJusta ? "bg-emerald-600" : "bg-amber-500"}`}><CheckCircle2 className="h-4 w-4"/></span><div><p className={`text-sm font-extrabold ${globalJusta ? "text-emerald-800" : "text-amber-800"}`}>Monto Global: {licitacion.estado} / En Margen</p><p className="mt-1 text-xs leading-5 text-slate-600">{detalleMonto}</p></div></div>
        {licitacion.articulos_sobreprecio > 0 && <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-extrabold text-red-800"><AlertTriangle className="h-5 w-5 shrink-0"/><span>{licitacion.alerta_interna}</span><span className="ml-auto text-xs font-semibold text-red-700">{licitacion.articulos_alto_riesgo} sobrevalorados · {licitacion.articulos_alerta_amarilla} irregulares</span></div>}
        <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-600">{licitacion.nota_metodologica}</p>
      </div>
      <div className="mt-4"><ImpactoFinancieroPanel licitacion={licitacion} compacto/></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{[["PRODUCTOS MONITOREADOS", totalProductos], ["EVALUACIONES", resumen.total_evaluaciones]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 bg-white/80 p-3"><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">{label}</p><p className="mt-1 text-lg font-extrabold text-slate-900">{value}</p></div>)}<div className="rounded-xl border border-slate-200 bg-white/80 p-3"><p className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400"><Clock3 className="h-3 w-3"/>ÚLTIMA ACTUALIZACIÓN</p><p className="mt-1 text-xs font-bold text-slate-700">{ultimaActualizacion > 0 ? formatearFecha(ultimaActualizacion) : "Sin evaluaciones"}</p></div></div>
    </div>
    <div className="relative flex h-fit self-start flex-col gap-4 overflow-hidden rounded-3xl bg-[#002D62] p-5 text-white shadow-lg shadow-ultramar/20 sm:p-6"><MapaRD className="pointer-events-none absolute -right-10 -top-8 h-56 w-56 text-white/10"/><div className="relative"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/60">ÍNDICE DE ALTO RIESGO</p><p className="mt-2 text-5xl font-black tracking-tight">{formatearPorcentaje(resumen.porcentaje_alto_riesgo)}</p><p className="mt-2 max-w-[15rem] text-xs leading-5 text-white/70">Proporción de artículos de esta versión con sobreprecio superior al 15 % frente al catálogo de mercado.</p></div><GraficoRiesgo resumen={resumen}/><div className="relative flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-white/70"><Scale className="h-3.5 w-3.5 shrink-0"/>Umbral de alto riesgo: sobreprecio mayor al 15 %.</div></div>
  </div></section>;
}

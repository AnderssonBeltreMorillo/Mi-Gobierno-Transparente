import type { Licitacion } from "../types";
import { calcularImpactoFinanciero, formatearRD } from "../lib/impactoFinanciero";

interface Props {
  licitacion: Licitacion;
  compacto?: boolean;
}

export function ImpactoFinancieroPanel({ licitacion, compacto = false }: Props) {
  const impacto = calcularImpactoFinanciero(licitacion);
  const metricas = [
    { titulo: "Monto total licitado", valor: impacto.montoTotal, color: "text-slate-900" },
    {
      titulo: "Monto evaluable en productos",
      valor: impacto.montoEvaluable,
      color: "text-ultramar",
      detalle: `Servicios/otros excluidos: ${formatearRD(impacto.montoNoEvaluable)} (${porcentaje(impacto.porcentajeMedible)} productos medibles)`,
    },
    { titulo: "Monto en supermercados · catálogo", valor: impacto.montoMercado, color: "text-emerald-700" },
    { titulo: "Sobreprecio total · sobrevalorado + irregular", valor: impacto.excedenteBruto, color: "text-[#CE1126]" },
  ];

  return (
    <section
      aria-label="Impacto Financiero de Sobrevaloración en RD$"
      className={`rounded-2xl border border-slate-200 bg-white ${compacto ? "p-3" : "p-4 sm:p-5"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-black uppercase tracking-[0.12em] text-slate-700">
          Impacto Financiero de Sobrevaloración (RD$)
        </h3>
        <span className="text-[10px] text-slate-400">Estimación por versión · catálogo de referencia</span>
      </div>
      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-2">
        {metricas.map((metrica, index) => (
          <div
            key={metrica.titulo}
            className={`min-w-0 rounded-xl border px-3 py-3 ${index === 3 ? "border-[#CE1126]/25 bg-red-50/50" : "border-slate-100 bg-slate-50/70"}`}
          >
            <p className="text-[9px] font-bold uppercase leading-4 tracking-[0.1em] text-slate-500">{metrica.titulo}</p>
            <p className={`mt-1 min-w-0 break-words text-base font-bold tabular-nums lg:text-lg ${metrica.color}`}>
              {index === 3 ? "+" : ""}{formatearRD(metrica.valor)}
            </p>
            {metrica.detalle && <p className="mt-1 text-[10px] leading-4 text-slate-600">{metrica.detalle}</p>}
            {index === 3 && (
              <p className="mt-1 text-[10px] leading-4 text-slate-600">
                Sobrevalorado: {formatearRD(impacto.sobrevalorado)} · Irregular: {formatearRD(impacto.irregular)}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function porcentaje(valor: number): string {
  return `${Number.isInteger(valor) ? valor.toFixed(0) : valor.toFixed(2)}%`;
}

function versionesOriginales(licitaciones: Licitacion[]): Licitacion[] {
  const originales = new Map<string, Licitacion>();
  for (const licitacion of licitaciones) {
    const existente = originales.get(licitacion.codigo);
    if (!existente || Number(licitacion.version) < Number(existente.version)) {
      originales.set(licitacion.codigo, licitacion);
    }
  }
  return [...originales.values()];
}

export function ResumenImpactoLicitaciones({ licitaciones }: { licitaciones: Licitacion[] }) {
  const originales = versionesOriginales(Array.isArray(licitaciones) ? licitaciones.filter(Boolean) : []);
  const sumas = originales.map(calcularImpactoFinanciero).reduce((total, actual) => ({
    montoTotal: total.montoTotal + actual.montoTotal,
    montoEvaluable: total.montoEvaluable + actual.montoEvaluable,
    montoMercado: total.montoMercado + actual.montoMercado,
    excedenteBruto: total.excedenteBruto + actual.excedenteBruto,
  }), { montoTotal: 0, montoEvaluable: 0, montoMercado: 0, excedenteBruto: 0 });
  const expediente = (Array.isArray(licitaciones) ? licitaciones : [])
    .filter((licitacion) => licitacion?.codigo === "DASAC-CCC-LPA-2026-0011")
    .sort((a, b) => Number(a.version) - Number(b.version));
  const original = expediente.find((licitacion) => Number(licitacion.version) === 1);
  const enmienda = expediente.find((licitacion) => Number(licitacion.version) > 1);

  return (
    <section aria-label="Resumen financiero sin duplicar las versiones del mismo expediente" className="mt-5 rounded-2xl border border-ultramar/15 bg-ultramar/[0.03] p-4 sm:p-5">
      <h3 className="text-xs font-black uppercase tracking-[0.12em] text-slate-700">RESUMEN FINANCIERO DE LICITACIONES ANALIZADAS</h3>
      <p className="mt-1 text-[10px] text-slate-500">
        Se toma el Pliego Original por código de proceso como línea base de auditoría; las enmiendas se muestran como comparativo y no se suman dos veces.
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-100 bg-white px-3 py-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-500">Monto total analizado</p>
          <p className="mt-1 whitespace-nowrap text-sm font-black tabular-nums text-slate-900">{formatearRD(sumas.montoTotal)}</p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-white px-3 py-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-500">Monto mercado · referencia catálogo</p>
          <p className="mt-1 whitespace-nowrap text-sm font-black tabular-nums text-ultramar">{formatearRD(sumas.montoMercado)}</p>
        </div>
        <div className="rounded-xl border border-[#CE1126]/25 bg-red-50/60 px-3 py-3">
          <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-500">Sobreprecio total bruto</p>
          <p className="mt-1 whitespace-nowrap text-sm font-black tabular-nums text-[#CE1126]">+{formatearRD(sumas.excedenteBruto)}</p>
        </div>
      </div>
      {original && enmienda && original.id_version !== enmienda.id_version && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-3">
            <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-slate-500">Pliego Original · {original.codigo}</p>
            <p className="mt-1 whitespace-nowrap text-sm font-black tabular-nums">{formatearRD(Number(original.monto_total) || 0)}</p>
          </div>
          <div className="rounded-xl border border-ultramar/20 bg-white px-3 py-3">
            <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-ultramar">Enmienda evaluada · {enmienda.codigo}</p>
            <p className="mt-1 whitespace-nowrap text-sm font-black tabular-nums text-ultramar">{formatearRD(Number(enmienda.monto_total) || 0)}</p>
          </div>
        </div>
      )}
    </section>
  );
}

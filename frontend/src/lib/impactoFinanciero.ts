import type { ArticuloAuditoria, Licitacion } from "../types";

export interface ImpactoFinanciero {
  montoTotal: number;
  montoNoEvaluable: number;
  montoEvaluable: number;
  porcentajeMedible: number;
  montoMercado: number;
  excedenteBruto: number;
  sobrevalorado: number;
  irregular: number;
}

function totalExcedente(articulos: ArticuloAuditoria[], estado: ArticuloAuditoria["estado"]): number {
  return (Array.isArray(articulos) ? articulos : []).filter(Boolean)
    .filter((articulo) => articulo.estado === estado && Number(articulo.diferencia) > 0)
    .reduce((total, articulo) => total + Number(articulo.diferencia) * articulo.cantidad, 0);
}

export function calcularImpactoFinanciero(licitacion: Licitacion): ImpactoFinanciero {
  const articulos = Array.isArray(licitacion?.auditoria_renglones) ? licitacion.auditoria_renglones : [];
  const sobrevalorado = totalExcedente(articulos, "ALTO_RIESGO");
  const irregular = totalExcedente(articulos, "ALERTA_AMARILLA");
  const excedenteBruto = sobrevalorado + irregular;
  const montoTotal = Number(licitacion?.monto_total) || 0;
  const montoNoEvaluable = Number(licitacion.monto_no_evaluable ?? "0");
  const montoEvaluable = montoTotal - montoNoEvaluable;

  return {
    montoTotal,
    montoNoEvaluable,
    montoEvaluable,
    porcentajeMedible: montoTotal > 0 ? montoEvaluable / montoTotal * 100 : 0,
    montoMercado: Number(licitacion?.monto_mercado) || 0,
    excedenteBruto,
    sobrevalorado,
    irregular,
  };
}

export function formatearRD(value: number): string {
  return `RD$ ${value.toLocaleString("es-DO", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

import { Package, Scale } from "lucide-react";
import type { ArticuloAuditoria, FuenteCatalogo, NivelRiesgo } from "../types";
import { obtenerFuentesMercado } from "../lib/fuentes";
import { EtiquetaRiesgo } from "./EtiquetaRiesgo";

interface Props {
  articulos: ArticuloAuditoria[];
  enlaceDgcp: string;
}

function riesgo(estado: ArticuloAuditoria["estado"]): NivelRiesgo {
  if (estado === "ALTO_RIESGO") return "alto_riesgo";
  if (estado === "ALERTA_AMARILLA") return "alerta_amarilla";
  return "precio_justo";
}

function nombreSupermercado(fuente: string | null | undefined): string {
  if (typeof fuente !== "string" || !fuente.trim()) return "Catálogo";
  const etiqueta = fuente.split("|")[0]?.trim();
  const valor = etiqueta || fuente;
  const nombreExplicito = ["Nacional", "Jumbo", "La Sirena", "Plaza Lama"].find(
    (nombre) => valor.toLocaleLowerCase("es").includes(nombre.toLocaleLowerCase("es")),
  );
  if (nombreExplicito) return nombreExplicito;

  const url = fuente.match(/https?:\/\/\S+/i)?.[0];
  if (!url) return valor || "Catálogo";
  try {
    const dominio = new URL(url).hostname.toLocaleLowerCase("es");
    if (dominio.includes("nacional")) return "Nacional";
    if (dominio.includes("jumbo")) return "Jumbo";
    if (dominio.includes("sirena")) return "La Sirena";
    if (dominio.includes("plazalama")) return "Plaza Lama";
  } catch {
    return valor || "Catálogo";
  }
  return "Catálogo";
}

function moneda(valor: number): string {
  return valor.toLocaleString("es-DO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function montoConSigno(valor: number): string {
  const signo = valor > 0 ? "+" : valor < 0 ? "-" : "";
  return `${signo}RD$ ${moneda(Math.abs(valor))}`;
}

function fuentesPara(articulo: ArticuloAuditoria): FuenteCatalogo[] {
  if (articulo.fuentes_mercado?.length) return articulo.fuentes_mercado;
  return obtenerFuentesMercado(articulo.producto);
}

export function TablaAuditoriaVersion({ articulos, enlaceDgcp }: Props) {
  const ordenados = (Array.isArray(articulos) ? articulos : []).filter(Boolean).sort((a, b) => {
    const peso = (estado: ArticuloAuditoria["estado"]) => estado === "ALTO_RIESGO" ? 3 : estado === "ALERTA_AMARILLA" ? 2 : 1;
    return peso(b.estado) - peso(a.estado) || Number(b.sobreprecio) - Number(a.sobreprecio);
  });

  return <div className="max-w-full touch-pan-x overflow-x-auto overscroll-x-contain scroll-smooth rounded-2xl border border-slate-200 bg-white shadow-sm"><table className="w-full min-w-[1180px] border-collapse text-left"><caption className="sr-only">Auditoría financiera por renglón, ordenada por nivel de riesgo</caption><thead><tr className="bg-ultramar/[0.04] text-center text-[9px] font-black uppercase tracking-[0.14em] text-ultramar"><th colSpan={3} className="border-b border-slate-200 px-3 py-2">Datos de licitación</th><th className="border-b border-slate-200 px-3 py-2">Datos del mercado</th><th colSpan={3} className="border-b border-slate-200 px-3 py-2">Valoraciones matemáticas del sistema</th><th rowSpan={2} className="border-b border-slate-200 px-3 py-3">Fuentes</th></tr><tr className="border-b border-slate-200 bg-slate-50 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500"><th className="px-3 py-3 text-left">Producto</th><th className="whitespace-nowrap px-3 py-3 text-right">Cantidad</th><th className="whitespace-nowrap px-3 py-3 text-right">Precio licitado</th><th className="whitespace-nowrap px-3 py-3 text-right">Precio mercado</th><th className="whitespace-nowrap px-3 py-3 text-right">Diferencia</th><th className="whitespace-nowrap px-3 py-3">Sobreprecio</th><th className="whitespace-nowrap px-3 py-3">Etiqueta</th></tr></thead><tbody className="divide-y divide-slate-100">{ordenados.map((articulo) => {
    const cantidad = Number(articulo.cantidad) || 0;
    const licitado = Number(articulo.precio_licitado) || 0;
    const mercado = Number(articulo.precio_mercado) || 0;
    const diferencia = Number(articulo.diferencia) || 0;
    const sobreprecio = Number(articulo.sobreprecio) || 0;
    const nivel = riesgo(articulo.estado);
    const fuentes = fuentesPara(articulo).filter((fuente) => Boolean(fuente?.url));
    const nombreReferencia = nombreSupermercado(articulo.fuente_mercado);
    const referencia = fuentes.find((fuente) => fuente.nombre === nombreReferencia)?.nombre ?? nombreReferencia;
    const colorDiferencia = nivel === "alto_riesgo" ? "text-[#CE1126]" : nivel === "alerta_amarilla" ? "text-amber-700" : diferencia < 0 ? "text-emerald-700" : "text-slate-600";
    const colorBarra = nivel === "alto_riesgo" ? "bg-[#CE1126]" : nivel === "alerta_amarilla" ? "bg-amber-400" : "bg-emerald-500";
    const presentacion = articulo.presentacion_comercial?.trim() || "Presentación no especificada";
    const equivalencia = articulo.equivalencia?.trim() || presentacion;
    const mostrarPresentacion = presentacion !== equivalencia;
    return <tr key={articulo.producto} className="group transition hover:bg-slate-50/80"><td className="px-3 py-4"><div className="flex items-start gap-2"><span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-ultramar/5 text-ultramar"><Package className="h-4 w-4" aria-hidden="true"/></span><div className="min-w-0"><p className="text-sm font-bold text-slate-900">{articulo.producto}</p>{mostrarPresentacion && <p className="mt-1 text-[10px] leading-4 text-slate-500">({presentacion})</p>}{equivalencia && <p className="mt-1 inline-flex max-w-full items-start gap-1 rounded-md bg-ultramar/[0.06] px-1.5 py-0.5 text-[10px] font-semibold leading-4 text-ultramar"><Scale className="mt-0.5 h-3 w-3 shrink-0" aria-hidden="true"/><span className="min-w-0 break-words">{equivalencia}</span></p>}</div></div></td><td className="whitespace-nowrap px-3 py-4 text-right text-sm font-semibold tabular-nums text-slate-700">{cantidad.toLocaleString("es-DO")} UD</td><td className="whitespace-nowrap px-3 py-4 text-right text-sm font-bold tabular-nums text-slate-900"><span className="block">RD$ {moneda(licitado)}</span><span className="mt-1 block text-[10px] font-medium text-slate-500">Total: RD$ {moneda(licitado * cantidad)}</span></td><td className="whitespace-nowrap px-3 py-4 text-right text-sm font-semibold tabular-nums text-slate-700"><span className="block">RD$ {moneda(mercado)}</span><span className="mt-1 block text-[10px] font-medium text-slate-500">Total: RD$ {moneda(mercado * cantidad)}</span><span className="mt-1 block text-[9px] font-bold text-ultramar">Ref.: {referencia}</span></td><td className={`whitespace-nowrap px-3 py-4 text-right text-sm font-bold tabular-nums ${colorDiferencia}`}><span className="block">{montoConSigno(diferencia)}</span><span className="mt-1 block text-[10px] font-semibold">{montoConSigno(diferencia * cantidad)}</span></td><td className="whitespace-nowrap px-3 py-4"><div className="flex items-center gap-2"><span className={`text-sm font-extrabold tabular-nums ${colorDiferencia}`}>{moneda(sobreprecio)} %</span><span className="h-1.5 w-12 shrink-0 overflow-hidden rounded-full bg-slate-100"><span className={`block h-full rounded-full ${colorBarra}`} style={{ width: `${Math.min(100, Math.max(0, sobreprecio))}%` }}/></span></div></td><td className="whitespace-nowrap px-3 py-4"><EtiquetaRiesgo nivel={nivel}/></td><td className="px-3 py-4"><div className="flex min-w-[130px] flex-col gap-1"><a href={enlaceDgcp} target="_blank" rel="noreferrer" className="inline-flex w-fit items-center gap-1 whitespace-nowrap text-[11px] font-bold text-ultramar hover:underline">DGCP ↗</a>{fuentes.map((fuente) => <a key={`${articulo.producto}-${fuente.nombre}`} href={fuente.url} target="_blank" rel="noreferrer" className="inline-flex w-fit items-center gap-1 whitespace-nowrap text-[11px] font-semibold text-slate-500 hover:text-ultramar hover:underline">{fuente.nombre} ↗</a>)}</div></td></tr>;
  })}</tbody></table></div>;
}

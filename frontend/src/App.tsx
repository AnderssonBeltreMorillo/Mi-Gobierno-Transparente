import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertCircle, ExternalLink } from "lucide-react";
import { EstadoCarga, EstadoError } from "./components/EstadoCarga";
import { DetalleErrorBoundary } from "./components/DetalleErrorBoundary";
import { Filtros } from "./components/Filtros";
import { Header } from "./components/Header";
import { ImpactoFinancieroPanel, ResumenImpactoLicitaciones } from "./components/ImpactoFinanciero";
import { ResumenCaso } from "./components/ResumenCaso";
import { ResumenKpis } from "./components/ResumenKpis";
import { TablaAuditoriaVersion } from "./components/TablaAuditoriaVersion";
import { obtenerDashboard } from "./lib/api";
import { formatearFechaISO } from "./lib/formato";
import { FUENTE_DGCP, FUENTES_MERCADO } from "./lib/fuentes";
import type { ArticuloAuditoria, ConteosRiesgo, DashboardData, FiltroRiesgo, Licitacion, LicitacionAgrupada, ResumenRiesgo } from "./types";

function esCancelacion(causa: unknown): boolean {
  return (causa instanceof DOMException && causa.name === "AbortError") || (causa instanceof Error && causa.name === "AbortError");
}

function riesgoFiltro(estado: ArticuloAuditoria["estado"]): Exclude<FiltroRiesgo, "todos"> {
  return estado === "ALTO_RIESGO" ? "alto_riesgo" : estado === "ALERTA_AMARILLA" ? "alerta_amarilla" : "precio_justo";
}

function moneda(value: string): string {
  return (Number(value) || 0).toLocaleString("es-DO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function comoObjeto(valor: unknown): Record<string, unknown> {
  return valor !== null && typeof valor === "object" && !Array.isArray(valor)
    ? valor as Record<string, unknown>
    : {};
}

function comoTexto(valor: unknown, defecto = ""): string {
  return typeof valor === "string" && valor.trim() ? valor : defecto;
}

function comoNumero(valor: unknown, defecto = 0): number {
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : defecto;
}

function normalizarLicitacion(valor: unknown, indice: number): Licitacion | null {
  const datos = comoObjeto(valor);
  const codigo = comoTexto(datos.codigo ?? datos.codigo_proceso);
  if (!codigo) return null;

  const version = Math.max(1, comoNumero(datos.version, indice + 1));
  const filasRaw = datos.auditoria_renglones ?? datos.renglones ?? datos.productos ?? [];
  const filas = Array.isArray(filasRaw) ? filasRaw : [];
  const auditoria = filas.map((filaRaw) => {
    const fila = comoObjeto(filaRaw);
    const riesgo = comoTexto(fila.estado ?? fila.nivel_riesgo).toUpperCase();
    const estado: ArticuloAuditoria["estado"] = riesgo.includes("ALTO")
      ? "ALTO_RIESGO"
      : riesgo.includes("ALERTA") || riesgo.includes("IRREGULAR")
        ? "ALERTA_AMARILLA"
        : "PRECIO_JUSTO";
    const fuentesRaw = fila.fuentes_mercado ?? fila.fuentes ?? [];
    const fuentes = Array.isArray(fuentesRaw)
      ? fuentesRaw.map((fuenteRaw) => {
          const fuente = comoObjeto(fuenteRaw);
          return {
            nombre: comoTexto(fuente.nombre, "Catálogo"),
            url: comoTexto(fuente.url),
          };
        }).filter((fuente) => Boolean(fuente.url))
      : [];
    const fuenteMercadoRaw = fila.fuente_mercado;
    const fuenteMercado = typeof fuenteMercadoRaw === "object" && fuenteMercadoRaw !== null
      ? `${comoTexto(comoObjeto(fuenteMercadoRaw).nombre)} | ${comoTexto(comoObjeto(fuenteMercadoRaw).url)}`.trim()
      : comoTexto(fuenteMercadoRaw);
    const presentacion = comoTexto(fila.presentacion_comercial ?? fila.unidad_medida, "Presentación no especificada");
    return {
      producto: comoTexto(fila.producto ?? fila.nombre ?? fila.descripcion_usuario ?? fila.descripcion_articulo, "Producto sin descripción"),
      cantidad: comoNumero(fila.cantidad),
      precio_licitado: String(comoNumero(fila.precio_licitado ?? fila.precio_unitario_estimado)),
      precio_mercado: String(comoNumero(fila.precio_mercado)),
      diferencia: String(comoNumero(fila.diferencia)),
      sobreprecio: String(comoNumero(fila.sobreprecio)),
      estado,
      presentacion_comercial: presentacion,
      equivalencia: comoTexto(fila.equivalencia, presentacion),
      fuente_mercado: fuenteMercado,
      fuentes_mercado: fuentes,
    } satisfies ArticuloAuditoria;
  });
  const estadoRaw = comoTexto(datos.estado);
  const estado: Licitacion["estado"] = estadoRaw === "Justa" || estadoRaw === "Sobrevalorada"
    ? estadoRaw
    : "Irregular";
  return {
    id_version: comoTexto(datos.id_version, `v${version}`),
    version,
    codigo,
    titulo: comoTexto(datos.titulo, `${codigo} (Pliego Original)`),
    institucion: comoTexto(datos.institucion ?? datos.unidad_compra, "Institución no especificada"),
    fecha_publicacion: formatearFechaISO(comoTexto(datos.fecha_publicacion, "Fecha no disponible")),
    monto_total: String(comoNumero(datos.monto_total ?? datos.monto_estimado)),
    monto_mercado: String(comoNumero(datos.monto_mercado)),
    monto_no_evaluable: String(comoNumero(datos.monto_no_evaluable)),
    diferencia_global: String(comoNumero(datos.diferencia_global)),
    sobreprecio: String(comoNumero(datos.sobreprecio)),
    estado,
    estado_proceso: comoTexto(datos.estado_proceso, "Estado no disponible"),
    articulos_sobreprecio: comoNumero(datos.articulos_sobreprecio),
    articulos_alerta_amarilla: comoNumero(datos.articulos_alerta_amarilla),
    articulos_alto_riesgo: comoNumero(datos.articulos_alto_riesgo),
    alerta_interna: comoTexto(datos.alerta_interna),
    nota_metodologica: comoTexto(datos.nota_metodologica),
    enlace_dgcp: comoTexto(datos.enlace_dgcp ?? datos.url, "https://datosabiertos.dgcp.gob.do/data-compras"),
    auditoria_renglones: auditoria,
  };
}

function agruparLicitaciones(licitaciones: Licitacion[]): LicitacionAgrupada[] {
  const grupos = new Map<string, Licitacion[]>();
  for (const licitacion of licitaciones) {
    const versiones = grupos.get(licitacion.codigo) ?? [];
    versiones.push(licitacion);
    grupos.set(licitacion.codigo, versiones);
  }
  return [...grupos.values()].map((versiones) => ({
    original: [...versiones].sort((a, b) => a.version - b.version)[0],
    versiones: [...versiones].sort((a, b) => a.version - b.version),
  }));
}

function TarjetaLicitacion({ grupo, onClick }: { grupo: LicitacionAgrupada; onClick: (version: Licitacion) => void }) {
  const { original, versiones } = grupo;
  return <article className="mt-5 w-full rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-ultramar/30 hover:shadow-md"><div role="button" tabIndex={0} onClick={() => onClick(original)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onClick(original); } }} className="cursor-pointer text-left outline-none focus-visible:ring-2 focus-visible:ring-ultramar"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-black text-slate-900">{original.titulo}</p><p className="mt-1 text-xs text-slate-500">{original.institucion} · Publicación: {original.fecha_publicacion}</p><p className="mt-1 text-xs font-semibold text-slate-600">{original.estado_proceso}</p></div><div className="flex flex-wrap gap-2"><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">Monto Global: {original.estado} / En Margen</span>{original.articulos_sobreprecio > 0 && <span className="rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-red-700">{original.alerta_interna}</span>}</div></div><div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500"><span>Monto licitado: RD$ {moneda(original.monto_total)}</span><span>Mercado: RD$ {moneda(original.monto_mercado)}</span></div></div><div className="mt-4"><ImpactoFinancieroPanel licitacion={original} compacto/></div><p className="mt-3 text-xs leading-5 text-slate-500">{original.nota_metodologica}</p><div className="mt-4 rounded-xl border border-ultramar/10 bg-ultramar/[0.03] p-3"><p className="text-[10px] font-black uppercase tracking-[0.12em] text-ultramar">Historial de Versiones y Enmiendas Evaluadas</p><div className="mt-2 flex flex-wrap gap-2">{versiones.map((version) => <button key={version.id_version} type="button" onClick={() => onClick(version)} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-bold text-slate-600 hover:border-ultramar hover:text-ultramar">{version.titulo.replace(`${version.codigo} (`, "").replace(")", "")} · RD$ {moneda(version.monto_total)}</button>)}</div></div></article>;
}

export default function App() {
  const [datos, setDatos] = useState<DashboardData | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<FiltroRiesgo>("todos");
  const [busqueda, setBusqueda] = useState("");
  const [detalle, setDetalle] = useState(false);
  const [versionActiva, setVersionActiva] = useState("v1");
  const licitaciones = useMemo(
    () => (Array.isArray(datos?.licitaciones)
      ? datos.licitaciones.map(normalizarLicitacion).filter((version): version is Licitacion => version !== null)
      : []),
    [datos?.licitaciones],
  );
  
  const grupos = useMemo(() => agruparLicitaciones(licitaciones), [licitaciones]);
  
  // FILTRADO GLOBAL EN LA VISTA PRINCIPAL
  const gruposFiltrados = useMemo(() => {
    if (!busqueda.trim()) return grupos;
    const termino = busqueda.trim().toLowerCase();
    return grupos.filter((grupo) => {
      const { original } = grupo;
      return (
        original.codigo.toLowerCase().includes(termino) ||
        original.titulo.toLowerCase().includes(termino) ||
        original.fecha_publicacion.toLowerCase().includes(termino)
      );
    });
  }, [grupos, busqueda]);

  const cargar = useCallback(async (signal?: AbortSignal, forceRefresh = false) => {
    setCargando(true);
    setError(null);
    try { setDatos(await obtenerDashboard(signal, forceRefresh)); }
    catch (causa) { if (!esCancelacion(causa)) setError(causa instanceof Error ? causa.message : "Error inesperado al consultar la API."); }
    finally { if (!signal?.aborted) setCargando(false); }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void cargar(controller.signal);
    return () => controller.abort();
  }, [cargar]);

  const licitacion = licitaciones.find((version) => version.id_version === versionActiva) ?? grupos[0]?.original ?? licitaciones[0];
  const articulos = Array.isArray(licitacion?.auditoria_renglones) ? licitacion.auditoria_renglones : [];
  const conteos = useMemo<ConteosRiesgo>(() => ({
    todos: articulos.length,
    precio_justo: articulos.filter((articulo) => articulo.estado === "PRECIO_JUSTO").length,
    alerta_amarilla: articulos.filter((articulo) => articulo.estado === "ALERTA_AMARILLA").length,
    alto_riesgo: articulos.filter((articulo) => articulo.estado === "ALTO_RIESGO").length,
  }), [articulos]);
  const resumenVersion = useMemo<ResumenRiesgo>(() => ({
    total_evaluaciones: articulos.length,
    precio_justo: conteos.precio_justo,
    alerta_amarilla: conteos.alerta_amarilla,
    alto_riesgo: conteos.alto_riesgo,
    porcentaje_alto_riesgo: articulos.length ? (conteos.alto_riesgo * 100 / articulos.length).toFixed(2) : "0.00",
  }), [articulos.length, conteos]);
  const ultimaActualizacion = useMemo(() => (Array.isArray(datos?.evaluaciones) ? datos.evaluaciones : []).filter(Boolean).reduce((maximo, evaluacion) => {
    const timestamp = new Date(evaluacion?.evaluado_en ?? 0).getTime();
    return Number.isNaN(timestamp) ? maximo : Math.max(maximo, timestamp);
  }, 0), [datos?.evaluaciones]);
  const filtrados = articulos.filter((articulo) => articulo && (filtro === "todos" || riesgoFiltro(articulo.estado) === filtro) && (articulo.producto ?? "").toLocaleLowerCase("es").includes(busqueda.trim().toLocaleLowerCase("es")));

  if (cargando && !datos) return <EstadoCarga/>;
  if (error && !datos) return <EstadoError mensaje={error} onReintentar={() => void cargar()}/>;
  if (!datos) return null;
  if (detalle && !licitacion) return <EstadoError mensaje="No hay versiones de licitación disponibles." onReintentar={() => void cargar()}/>;

  return <div className="relative isolate flex min-h-screen flex-col overflow-hidden overflow-x-hidden bg-canvas">
    <div aria-hidden="true" className="surface-grid pointer-events-none absolute inset-0 -z-10 opacity-50"/>
    <Header cargando={cargando} onRefresh={() => void cargar(undefined, true)}/>
    <main className="mx-auto flex-1 w-full max-w-7xl overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
      {error && <div className="mb-4 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800"><AlertCircle className="h-4 w-4 shrink-0"/>No se pudo actualizar la información: {error}. Se muestran los últimos datos cargados.</div>}
      {!detalle ? <>
        <section className="relative mb-6 overflow-hidden rounded-[2rem] bg-[#002D62] p-6 text-white shadow-xl sm:p-8"><div aria-hidden="true" className="absolute inset-y-0 right-0 w-2 bg-[#CE1126]"/><p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/65">Transparencia · eficiencia fiscal · integridad institucional</p><h2 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">Mi Gobierno Transparente</h2><p className="mt-3 max-w-4xl text-sm leading-6 text-white/85">Plataforma automatizada de auditoría continua e inteligencia de precios que cruza información de compras públicas de la DGCP con catálogos de comercios formales.</p><p className="mt-3 max-w-4xl text-sm leading-6 text-white/75">Su objetivo es transparentar el gasto público, detectar sobrevaloraciones por renglón y respaldar las medidas de eficiencia fiscal e integridad institucional promovidas por el presidente Luis Abinader Corona.</p></section>
        <section className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-ultramar/60">Historial del proceso · documentos oficiales</p>
          <h2 className="mt-1 text-2xl font-black text-slate-950">Licitaciones completas analizadas</h2>
          
          <div className="mt-6 mb-2">
            <input
              type="text"
              placeholder="Buscar por código (ej. DASAC-CCC...), título o fecha..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="w-full p-3 border border-slate-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm"
            />
          </div>

          <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{[["Licitaciones analizadas", grupos.length], ["Monto global en margen", grupos.filter((grupo) => grupo.original.estado === "Justa").length], ["Con renglones irregulares", grupos.filter((grupo) => grupo.original.articulos_alerta_amarilla > 0).length], ["Con renglones sobrevalorados", grupos.filter((grupo) => grupo.original.articulos_alto_riesgo > 0).length]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 px-3 py-2 text-center"><b className="block text-lg text-slate-900">{value}</b><span className="text-xs text-slate-500">{label}</span></div>)}</div>
          <p className="mt-3 text-xs leading-5 text-slate-500">Los KPIs y el resumen financiero toman el Pliego Original; las enmiendas permanecen disponibles en el historial.</p>
          <ResumenImpactoLicitaciones licitaciones={licitaciones}/>
          
          {gruposFiltrados.length > 0 ? (
            gruposFiltrados.map((grupo) => <TarjetaLicitacion key={grupo.original.codigo} grupo={grupo} onClick={(version) => { setVersionActiva(version.id_version); setDetalle(true); setBusqueda(""); }}/>)
          ) : (
            <p className="mt-8 text-center text-sm text-slate-500">No se encontraron licitaciones que coincidan con la búsqueda.</p>
          )}
        </section>
      </> : <DetalleErrorBoundary onVolver={() => setDetalle(false)}><>
        <button type="button" onClick={() => setDetalle(false)} className="mb-5 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50">← Volver al listado de licitaciones</button>
        <div role="tablist" aria-label="Versiones del procedimiento" className="mb-4 flex flex-wrap gap-2">{licitaciones.filter((version) => version.codigo === licitacion.codigo).map((version) => <button key={version.id_version} type="button" role="tab" aria-selected={versionActiva === version.id_version} onClick={() => { setVersionActiva(version.id_version); setFiltro("todos"); setBusqueda(""); }} className={`rounded-full border px-4 py-2 text-xs font-bold ${versionActiva === version.id_version ? "border-ultramar bg-ultramar text-white" : "border-slate-200 bg-white text-slate-600"}`}>{version.titulo}</button>)}</div>
        <div className="mb-4 rounded-2xl border border-ultramar/15 bg-ultramar/5 p-4 text-sm"><b>{licitacion.titulo}</b> · {licitacion.estado_proceso} · Publicación {licitacion.fecha_publicacion} · <a className="font-bold text-ultramar underline" href={licitacion.enlace_dgcp} target="_blank" rel="noreferrer">Ver expediente oficial DGCP</a></div>
        <div className="mb-8 space-y-4"><ResumenCaso resumen={resumenVersion} totalProductos={articulos.length} ultimaActualizacion={ultimaActualizacion} licitacion={licitacion}/><ResumenKpis resumen={resumenVersion}/></div>
        <section><div className="mb-4"><p className="text-[11px] font-bold uppercase tracking-[0.18em] text-ultramar/60">Auditoría de precios</p><h2 className="mt-1 text-2xl font-black text-slate-950">Comparación por producto</h2><p className="mt-1 text-sm text-slate-500">Filas ordenadas de mayor riesgo a precio justo. Los importes inferiores muestran el total de renglón multiplicado por su cantidad.</p></div><Filtros filtro={filtro} onCambiarFiltro={setFiltro} busqueda={busqueda} onCambiarBusqueda={setBusqueda} conteos={conteos}/>{filtrados.length ? <div className="mt-4"><p className="mb-2 text-center text-[11px] font-semibold text-slate-400 lg:hidden">← Desliza la tabla para ver precios y fuentes →</p><TablaAuditoriaVersion articulos={filtrados} enlaceDgcp={licitacion.enlace_dgcp}/></div> : <p className="mt-4 rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">No hay artículos para los filtros seleccionados.</p>}</section>
      </></DetalleErrorBoundary>}
    </main>
    <footer className="mt-auto border-t border-slate-200 bg-white/70"><div className="mx-auto grid max-w-7xl gap-4 px-4 py-6 text-xs text-slate-500 sm:px-6 lg:grid-cols-3 lg:items-center lg:px-8"><div><p className="font-semibold text-slate-600">Fuentes oficiales y catálogos comerciales</p><div className="mt-2 flex flex-wrap gap-3">{[FUENTE_DGCP, ...Object.values(FUENTES_MERCADO)].map((fuente) => <a key={fuente.nombre} href={fuente.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 font-semibold hover:text-ultramar">{fuente.nombre}<ExternalLink className="h-3 w-3"/></a>)}</div></div><p className="text-center font-bold leading-5 text-slate-700">Desarrollado por Andersson Beltre, estudiante de término de Desarrollo de Software en el Instituto Tecnológico de Las Américas (ITLA).</p><p className="text-right font-semibold text-slate-600 lg:justify-end">Auditoría pública automatizada conforme a la Ley 340-06 de Compras y Contrataciones.</p></div></footer>
  </div>;
}
export type NivelRiesgo = "precio_justo" | "alerta_amarilla" | "alto_riesgo";

export interface Producto {
  id: string;
  nombre: string;
  categoria: string;
  unidad_medida: string;
  marca: string | null;
  descripcion: string | null;
  activo: boolean;
}

export interface Evaluacion {
  id: string;
  producto_id: string;
  precio_reportado_id: string;
  precio_mercado_id: string;
  monto_reportado: string;
  monto_mercado: string;
  moneda: string;
  diferencia: string;
  excedente: string;
  sobreprecio_porcentaje: string;
  nivel_riesgo: NivelRiesgo;
  dentro_de_tolerancia: boolean;
  requiere_intervencion: boolean;
  alerta_amarilla_desde_porcentaje: string;
  alto_riesgo_desde_porcentaje: string;
  evaluado_en: string;
  version_regla: string;
  observacion: string | null;
}

export interface ResumenRiesgo {
  total_evaluaciones: number;
  precio_justo: number;
  alerta_amarilla: number;
  alto_riesgo: number;
  porcentaje_alto_riesgo: string;
}

export interface Comparacion {
  producto: Producto;
  evaluacion: Evaluacion;
}

export interface DashboardData {
  productos: Producto[];
  evaluaciones: Evaluacion[];
  resumen: ResumenRiesgo;
  licitaciones: Licitacion[];
}

export interface Licitacion {
  id_version: string;
  version: number;
  codigo: string;
  titulo: string;
  institucion: string;
  fecha_publicacion: string;
  monto_total: string;
  monto_mercado: string;
  monto_no_evaluable?: string;
  diferencia_global: string;
  sobreprecio: string;
  estado: "Justa" | "Irregular" | "Sobrevalorada";
  estado_proceso: string;
  articulos_sobreprecio: number;
  articulos_alerta_amarilla: number;
  articulos_alto_riesgo: number;
  alerta_interna: string;
  nota_metodologica: string;
  enlace_dgcp: string;
  auditoria_renglones: ArticuloAuditoria[];
}

export interface LicitacionAgrupada {
  original: Licitacion;
  versiones: Licitacion[];
}

export interface ArticuloAuditoria {
  producto: string;
  cantidad: number;
  precio_licitado: string;
  precio_mercado: string;
  diferencia: string;
  sobreprecio: string;
  estado: "PRECIO_JUSTO" | "ALERTA_AMARILLA" | "ALTO_RIESGO";
  presentacion_comercial: string;
  equivalencia?: string;
  fuente_mercado: string;
  fuentes_mercado?: FuenteCatalogo[];
}

export interface FuenteCatalogo {
  nombre: string;
  url: string;
}

export type FiltroRiesgo = "todos" | NivelRiesgo;

export type ConteosRiesgo = Record<FiltroRiesgo, number>;

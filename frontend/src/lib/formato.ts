const FORMATO_NUMERO = new Intl.NumberFormat("es-DO", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const FORMATO_FECHA = new Intl.DateTimeFormat("es-DO", {
  dateStyle: "medium",
  timeStyle: "short",
});

const ETIQUETAS_UNIDAD: Record<string, string> = {
  unidad: "Unidad",
  kilogramo: "Kilogramo",
  gramo: "Gramo",
  litro: "Litro",
  mililitro: "Mililitro",
  paquete: "Paquete",
  caja: "Caja",
};

const ETIQUETAS_CATEGORIA: Record<string, string> = {
  alimentos: "Alimentos",
  aseo: "Aseo",
};

export function aNumero(valor: string | number): number {
  if (typeof valor === "number") {
    return Number.isFinite(valor) ? valor : 0;
  }
  const numero = Number(valor);
  return Number.isFinite(numero) ? numero : 0;
}

export function formatearMoneda(valor: string | number, moneda = "DOP"): string {
  const simbolo = moneda === "DOP" ? "RD$" : moneda;
  return `${simbolo} ${FORMATO_NUMERO.format(aNumero(valor))}`;
}

export function formatearPorcentaje(valor: string | number): string {
  return `${FORMATO_NUMERO.format(aNumero(valor))} %`;
}

export function formatearFecha(valor: string | number | Date): string {
  const fecha = valor instanceof Date ? valor : new Date(valor);
  if (Number.isNaN(fecha.getTime())) {
    return "Sin fecha";
  }
  return FORMATO_FECHA.format(fecha);
}

export function formatearFechaISO(valor: string): string {
  const texto = valor.trim();
  return texto ? texto.split("T")[0] : texto;
}

export function etiquetaUnidad(unidad: string): string {
  return ETIQUETAS_UNIDAD[unidad] ?? unidad;
}

export function etiquetaCategoria(categoria: string): string {
  return ETIQUETAS_CATEGORIA[categoria] ?? categoria;
}

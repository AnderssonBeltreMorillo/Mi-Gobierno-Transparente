import type { Comparacion, Evaluacion, Producto } from "../types";

const PRIORIDAD_RIESGO: Record<string, number> = {
  alto_riesgo: 0,
  alerta_amarilla: 1,
  precio_justo: 2,
};

function tiempoDeEvaluacion(evaluacion: Evaluacion): number {
  const tiempo = new Date(evaluacion.evaluado_en).getTime();
  return Number.isNaN(tiempo) ? 0 : tiempo;
}

/**
 * Cruza productos y evaluaciones tomando la evaluación más reciente por
 * producto. Así la tabla no duplica filas si el seed se ejecuta varias veces.
 */
export function construirComparaciones(
  productos: Producto[],
  evaluaciones: Evaluacion[],
): Comparacion[] {
  const productosPorId = new Map(productos.map((producto) => [producto.id, producto]));
  const ultimasPorProducto = new Map<string, Evaluacion>();

  for (const evaluacion of evaluaciones) {
    const actual = ultimasPorProducto.get(evaluacion.producto_id);
    if (!actual || tiempoDeEvaluacion(evaluacion) > tiempoDeEvaluacion(actual)) {
      ultimasPorProducto.set(evaluacion.producto_id, evaluacion);
    }
  }

  return [...ultimasPorProducto.values()]
    .flatMap((evaluacion) => {
      const producto = productosPorId.get(evaluacion.producto_id);
      return producto ? [{ producto, evaluacion }] : [];
    })
    .sort((a, b) => {
      const prioridad =
        (PRIORIDAD_RIESGO[a.evaluacion.nivel_riesgo] ?? 9) -
        (PRIORIDAD_RIESGO[b.evaluacion.nivel_riesgo] ?? 9);
      if (prioridad !== 0) {
        return prioridad;
      }
      const sobreprecio =
        Number(b.evaluacion.sobreprecio_porcentaje) -
        Number(a.evaluacion.sobreprecio_porcentaje);
      if (sobreprecio !== 0) {
        return sobreprecio;
      }
      return a.producto.nombre.localeCompare(b.producto.nombre, "es");
    });
}

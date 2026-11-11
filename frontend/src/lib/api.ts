import type {
  DashboardData,
  Evaluacion,
  Licitacion,
  Producto,
  ResumenRiesgo,
} from "../types";

const URL_CONFIGURADA = import.meta.env.VITE_API_URL as string | undefined;

export const API_URL = (URL_CONFIGURADA ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);

interface RespuestaError {
  error?: {
    codigo?: string;
    mensaje?: string;
  };
}

async function solicitar<T>(ruta: string, signal?: AbortSignal, forceRefresh = false): Promise<T> {
  const separador = ruta.includes("?") ? "&" : "?";
  const respuesta = await fetch(`${API_URL}${ruta}${forceRefresh ? `${separador}force_refresh=true` : ""}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!respuesta.ok) {
    let mensaje = `La API respondió con estado ${respuesta.status}.`;
    try {
      const cuerpo = (await respuesta.json()) as RespuestaError;
      if (cuerpo.error?.mensaje) {
        mensaje = cuerpo.error.mensaje;
      }
    } catch {
      // El cuerpo no era JSON; se conserva el mensaje por defecto.
    }
    throw new Error(mensaje);
  }

  return (await respuesta.json()) as T;
}

export async function obtenerDashboard(
  signal?: AbortSignal,
  forceRefresh = false,
): Promise<DashboardData> {
  const [productos, evaluaciones, resumen, licitaciones] = await Promise.all([
    solicitar<Producto[]>("/productos", signal, forceRefresh),
    solicitar<Evaluacion[]>("/evaluaciones", signal, forceRefresh),
    solicitar<ResumenRiesgo>("/resumen-riesgo", signal, forceRefresh),
    solicitar<Licitacion[]>("/licitaciones", signal, forceRefresh),
  ]);

  return { productos, evaluaciones, resumen, licitaciones };
}

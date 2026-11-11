import { AlertTriangle, CheckCircle2, TrendingUp } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { NivelRiesgo } from "../types";

interface ConfiguracionEtiqueta {
  texto: string;
  icono: LucideIcon;
  clases: string;
}

const CONFIGURACION: Record<NivelRiesgo, ConfiguracionEtiqueta> = {
  precio_justo: {
    texto: "Precio Justo",
    icono: CheckCircle2,
    clases: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  alerta_amarilla: {
    texto: "Irregular",
    icono: AlertTriangle,
    clases: "border-amber-200 bg-amber-50 text-amber-700",
  },
  alto_riesgo: {
    texto: "Sobrevalorado",
    icono: TrendingUp,
    clases: "border-red-200 bg-red-50 text-bermellon",
  },
};

interface Props {
  nivel: NivelRiesgo;
  compacta?: boolean;
}

export function EtiquetaRiesgo({ nivel, compacta = false }: Props) {
  const configuracion = CONFIGURACION[nivel] ?? CONFIGURACION.alerta_amarilla;
  const Icono = configuracion.icono;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-bold ${configuracion.clases} ${
        compacta ? "px-2 py-1 text-[11px]" : "px-2.5 py-1 text-xs"
      }`}
    >
      <Icono
        className={compacta ? "h-3 w-3" : "h-3.5 w-3.5"}
        aria-hidden="true"
      />
      {configuracion.texto}
    </span>
  );
}

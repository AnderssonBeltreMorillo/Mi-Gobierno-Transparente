import { useId } from "react";

interface Props {
  className?: string;
}

/**
 * Silueta minimalista y estilizada de la República Dominicana, acompañada de
 * arcos coloniales geométricos. No reproduce la bandera ni el escudo nacional.
 */
export function MapaRD({ className = "" }: Props) {
  const patronId = `arcos-${useId().replace(/:/g, "")}`;

  return (
    <svg
      viewBox="0 0 320 240"
      className={className}
      aria-hidden="true"
      role="presentation"
    >
      <defs>
        <pattern
          id={patronId}
          width="30"
          height="30"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M3 26V15a12 12 0 0 1 24 0v11"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            opacity="0.45"
          />
        </pattern>
      </defs>

      <rect width="320" height="240" fill={`url(#${patronId})`} opacity="0.3" />

      <path
        d="M62 82c16-14 38-20 60-18 18 2 34-4 52-2 18 2 36 10 48 24 12 14 18 30 16 46-2 14-10 24-18 32-8 8-18 14-30 18-12 4-24 2-36 6-12 4-24 10-36 8-12-2-20-10-30-16-10-6-20-12-28-22-8-10-14-22-16-36-2-14 4-28 10-34 2-3 5-5 8-6Z"
        fill="currentColor"
      />
      <path
        d="M46 136c-12 2-24 8-34 16 10 6 22 4 34-2Z"
        fill="currentColor"
        opacity="0.85"
      />
      <path
        d="M238 132c10 4 20 14 24 26-10-4-18-10-26-16Z"
        fill="currentColor"
        opacity="0.85"
      />
      <path
        d="M222 86c10-6 22-8 30-4-8 6-18 10-26 12Z"
        fill="currentColor"
        opacity="0.7"
      />

      <circle cx="160" cy="128" r="3.5" fill="currentColor" />
      <circle
        cx="160"
        cy="128"
        r="9"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.45"
      />
    </svg>
  );
}

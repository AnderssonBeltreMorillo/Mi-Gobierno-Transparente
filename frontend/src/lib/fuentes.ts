export interface Fuente {
  nombre: string;
  url: string;
}

export const FUENTE_DGCP: Fuente = {
  nombre: "DGCP",
  url: "https://www.dgcp.gob.do/",
};

export const FUENTES_MERCADO = {
  bravo: { nombre: "Bravo", url: "https://superbravo.com.do/" },
  laSirena: { nombre: "La Sirena", url: "https://www.sirena.do/" },
  nacional: { nombre: "Nacional", url: "https://supermercadosnacional.com/" },
  jumbo: { nombre: "Jumbo", url: "https://www.jumbo.com.do/" },
} satisfies Record<string, Fuente>;

const FUENTES_POR_PRODUCTO: Record<string, Fuente[]> = {
  "azucar funda (1 libra)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282" },
    { nombre: "Jumbo", url: "https://jumbo.com.do/supermercado/despensa/azucar-y-edulcorantes/azucar" },
  ],
  "azucar funda (2 libras)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/azucar-blanca-refina-lider-2-lb-2140282" },
    { nombre: "Jumbo", url: "https://jumbo.com.do/supermercado/despensa/azucar-y-edulcorantes/azucar" },
  ],
  "canela sobre (2 onzas)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/canela-entera-60-gr-2168240" },
    { nombre: "La Sirena", url: "https://nuevo.sirena.do/supermercado/despensa/especias-y-condimentos" },
  ],
  "clavo dulce sobre (2 onzas)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/clavo-dulce-lider-50-gr-2168242" },
  ],
  "galletas de leche (7.4 onzas)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/galletas-de-leche-guarina-8-onz-2021974" },
  ],
  "habichuela roja funda (2 libras)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/habichuela-roja-larga-lider-800-gr-2140272" },
    { nombre: "Jumbo", url: "https://jumbo.com.do/supermercado/despensa/arroz-cereales-y-legumbres/habichuelas/habichuela-roja-larga-lider-800-gr-2140272" },
    { nombre: "La Sirena", url: "https://nuevo.sirena.do/supermercado/despensa/arroz-habichuelas-y-otros-granos/habichuelas" },
    { nombre: "Bravo", url: "https://superbravo.com.do/un-viaje-de-especiales/" },
  ],
  "leche de coco (10.5 onzas)": [
    { nombre: "Jumbo", url: "https://jumbo.com.do/supermercado/panaderia-y-reposteria/reposteria/leche-y-crema-de-coco/leche-de-coco-la-famosa-10-5-onz-2033831" },
    { nombre: "La Sirena", url: "https://www.sirena.do/la-famosa-leche-coco-10-5-oz-1092050/p" },
  ],
  "leche evaporada (315 gramos)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/lacteos-y-huevos/leches/leche-evaporada-y-condensada" },
    { nombre: "Jumbo", url: "https://jumbo.com.do/leche-evaporada-carnation-312g-2002106" },
    { nombre: "La Sirena", url: "https://www.sirena.do/carnation-leche-evaporada-312-gr-1020771/p" },
  ],
  "malagueta sobre (2 onzas)": [
    { nombre: "Nacional", url: "https://supermercadosnacional.com/malagueta-entera-lider-50-gr-2168247" },
  ],
};

function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("es").trim();
}

export function obtenerFuentesMercado(nombreProducto: string): Fuente[] {
  return FUENTES_POR_PRODUCTO[normalizar(nombreProducto)] ?? [];
}

export function obtenerFuenteMercado(nombreProducto: string): Fuente {
  return obtenerFuentesMercado(nombreProducto)[0] ?? { nombre: "Nacional", url: FUENTES_MERCADO.nacional.url };
}

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/manrope";
import "./index.css";
import App from "./App";

const contenedor = document.getElementById("root");

if (!contenedor) {
  throw new Error("No se encontró el contenedor #root.");
}

createRoot(contenedor).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

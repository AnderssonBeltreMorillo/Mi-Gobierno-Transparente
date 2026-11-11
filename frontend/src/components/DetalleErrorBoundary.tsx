import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  onVolver: () => void;
}

interface State {
  fallo: boolean;
}

export class DetalleErrorBoundary extends Component<Props, State> {
  state: State = { fallo: false };

  static getDerivedStateFromError(): State {
    return { fallo: true };
  }

  componentDidCatch(_error: Error, _info: ErrorInfo): void {
    // La vista alternativa permite volver al listado sin perder la aplicación.
  }

  render() {
    if (this.state.fallo) {
      return (
        <section role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
          <h2 className="font-black">No se pudo mostrar esta versión</h2>
          <p className="mt-1">La ficha contiene un dato incompleto o inesperado. El listado sigue disponible.</p>
          <button type="button" onClick={this.props.onVolver} className="mt-4 rounded-full bg-ultramar px-4 py-2 text-xs font-bold text-white">
            Volver al listado
          </button>
        </section>
      );
    }
    return this.props.children;
  }
}

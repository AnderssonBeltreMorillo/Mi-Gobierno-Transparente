"""Suite de pruebas.

Agrega ``src/`` al ``sys.path`` para poder ejecutar las pruebas sin instalar el
paquete. En un proyecto real esto se resuelve con ``pip install -e .`` o con la
configuración ``pythonpath`` de pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

"""Caché stale-while-revalidate para proteger Firestore durante picos de tráfico."""

from __future__ import annotations

import logging
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event, RLock
from time import monotonic
from typing import Any, TypeVar, cast

_LOGGER = logging.getLogger(__name__)
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class _Entrada:
    expira_en: float
    valor: Any


class CacheTTL:
    """Sirve valores desde memoria y solo una lectura de relleno por clave.

    Las entradas expiradas se sirven mientras se recargan en segundo plano.
    ``force_refresh`` acepta como máximo una recarga real cada intervalo global
    para todas las claves de la instancia.
    """

    def __init__(
        self,
        ttl_segundos: float = 300.0,
        *,
        intervalo_force_refresh: float = 60.0,
        max_entradas: int = 512,
    ) -> None:
        if ttl_segundos <= 0 or intervalo_force_refresh <= 0 or max_entradas <= 0:
            raise ValueError("TTL, intervalo force_refresh y capacidad deben ser positivos.")
        self._ttl = ttl_segundos
        self._intervalo_force_refresh = intervalo_force_refresh
        self._max_entradas = max_entradas
        self._entradas: OrderedDict[str, _Entrada] = OrderedDict()
        self._lock = RLock()
        self._cargas: dict[str, Event] = {}
        self._errores: dict[str, Exception] = {}
        self._recargas: set[str] = set()
        self._ultimo_force_refresh = float("-inf")
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache-firestore")

    def obtener(
        self,
        clave: str,
        cargar: Callable[[], _T],
        *,
        force_refresh: bool = False,
    ) -> _T:
        ahora = monotonic()
        evento: Event | None = None
        propietario = False
        with self._lock:
            entrada = self._entradas.get(clave)
            if entrada is not None:
                self._entradas.move_to_end(clave)
                if force_refresh:
                    permitido = ahora - self._ultimo_force_refresh >= self._intervalo_force_refresh
                    if permitido:
                        self._ultimo_force_refresh = ahora
                        self._programar_recarga(clave, cargar)
                elif entrada.expira_en <= ahora:
                    self._programar_recarga(clave, cargar)
                return cast(_T, entrada.valor)

            # En frío se hace una única carga sincrónica; el resto de
            # solicitudes espera esa misma lectura, no inicia lecturas paralelas.
            evento = self._cargas.get(clave)
            if evento is None:
                evento = Event()
                self._cargas[clave] = evento
                propietario = True

        if propietario:
            try:
                valor = cargar()
            except Exception as exc:
                with self._lock:
                    self._errores[clave] = exc
                    self._cargas.pop(clave, None)
                    evento.set()
                raise
            with self._lock:
                self._guardar(clave, valor, monotonic())
                self._errores.pop(clave, None)
                self._cargas.pop(clave, None)
                evento.set()
            return valor

        evento.wait()
        with self._lock:
            entrada = self._entradas.get(clave)
            if entrada is not None:
                self._entradas.move_to_end(clave)
                return cast(_T, entrada.valor)
            error = self._errores.get(clave)
        if error is not None:
            raise error
        return self.obtener(clave, cargar, force_refresh=False)

    def _programar_recarga(self, clave: str, cargar: Callable[[], Any]) -> None:
        if clave in self._recargas:
            return
        self._recargas.add(clave)
        self._executor.submit(self._recargar, clave, cargar)

    def _recargar(self, clave: str, cargar: Callable[[], Any]) -> None:
        try:
            valor = cargar()
        except Exception:
            _LOGGER.exception("Falló la recarga en segundo plano de la caché '%s'.", clave)
            with self._lock:
                entrada = self._entradas.get(clave)
                if entrada is not None:
                    # Un breve backoff evita volver a golpear Firestore mientras
                    # el valor previo sigue disponible para los visitantes.
                    self._entradas[clave] = _Entrada(monotonic() + 15.0, entrada.valor)
        else:
            with self._lock:
                self._guardar(clave, valor, monotonic())
        finally:
            with self._lock:
                self._recargas.discard(clave)

    def _guardar(self, clave: str, valor: Any, ahora: float) -> None:
        self._entradas[clave] = _Entrada(ahora + self._ttl, valor)
        self._entradas.move_to_end(clave)
        while len(self._entradas) > self._max_entradas:
            self._entradas.popitem(last=False)

    def limpiar(self) -> None:
        with self._lock:
            self._entradas.clear()
            self._errores.clear()
            self._ultimo_force_refresh = float("-inf")


cache_lecturas = CacheTTL(ttl_segundos=300.0, intervalo_force_refresh=60.0)

__all__ = ["CacheTTL", "cache_lecturas"]

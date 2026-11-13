from decimal import Decimal

from mi_gobierno_transparente.presentation.routers.licitaciones import (
    _fusionar_versiones_firestore,
    listar_licitaciones,
)


def test_historial_contiene_las_dos_versiones_oficiales_y_sus_totales() -> None:
    original, enmienda = listar_licitaciones()

    assert original["id_version"] == "v1"
    assert original["monto_total"] == "630000000.00"
    assert len(original["auditoria_renglones"]) == 8
    assert enmienda["id_version"] == "v2"
    assert enmienda["monto_total"] == "255000000.00"
    assert len(enmienda["auditoria_renglones"]) == 6


def test_auditoria_global_e_interna_son_independientes_y_conservan_ahorros() -> None:
    original, enmienda = listar_licitaciones()

    assert enmienda["estado"] == "Justa"
    assert enmienda["articulos_alto_riesgo"] == 2
    assert enmienda["articulos_alerta_amarilla"] == 2
    azucar = enmienda["auditoria_renglones"][0]
    assert Decimal(azucar["diferencia"]) == Decimal("-13.00")
    assert azucar["sobreprecio"] == "0.00"
    assert azucar["estado"] == "PRECIO_JUSTO"
    assert original["articulos_sobreprecio"] == 6


def test_versiones_incluyen_monto_no_evaluable_y_fuentes_formales() -> None:
    dominios_oficiales = ("supermercadosnacional.com", "jumbo.com.do", "sirena.do", "plazalama.com.do")
    for licitacion in listar_licitaciones():
        assert licitacion["monto_no_evaluable"] == "0.00"
        for articulo in licitacion["auditoria_renglones"]:
            fuentes = articulo["fuentes_mercado"]
            assert fuentes
            assert any(fuente["nombre"] == "Nacional" for fuente in fuentes) or any(
                fuente["nombre"] in {"Jumbo", "La Sirena"} for fuente in fuentes
            )
            for fuente in fuentes:
                dominio = fuente["url"].split("/")[2]
                assert any(dominio == oficial or dominio.endswith(f".{oficial}") for oficial in dominios_oficiales)


def test_historial_firestore_agrega_procesos_dgcp_sin_duplicar_versiones() -> None:
    auto = {
        "id_version": "auto-HFMP-DAF-CM-2026-0148",
        "version": 1,
        "codigo": "HFMP-DAF-CM-2026-0148",
        "auditoria_renglones": [],
    }

    class DocumentoFalso:
        id = "HFMP-DAF-CM-2026-0148"

        def to_dict(self) -> dict[str, object]:
            return {"codigo": self.id, "version_original": auto, "versiones": [auto]}

    class ColeccionFalsa:
        def stream(self) -> list[DocumentoFalso]:
            return [DocumentoFalso()]

    class ClienteFalso:
        def collection(self, _nombre: str) -> ColeccionFalsa:
            return ColeccionFalsa()

    historial = _fusionar_versiones_firestore(ClienteFalso())  # type: ignore[arg-type]

    coincidencias = [version for version in historial if version["codigo"] == auto["codigo"]]
    assert len(coincidencias) == 1
    assert coincidencias[0]["id_version"] == auto["id_version"]
    assert len([version for version in historial if version["codigo"] == "DASAC-CCC-LPA-2026-0011"]) == 2

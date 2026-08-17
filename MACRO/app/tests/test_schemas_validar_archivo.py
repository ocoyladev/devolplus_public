from MACRO.app.schemas.procesos import CasoValidacion, ValidarArchivoResponse


def test_caso_validacion_desde_dict_del_flujo():
    d = {
        "num_doc": "D1", "num_dev": "260-1", "num_ruc": "20123", "nombre": "ACME",
        "of_devolucion": "OF1", "tipo_exp": "ELECTRONICO", "is_of_multiple": False,
        "carpeta_existe": True, "paso_pptt": True,
        "insumo_final": {"completo": True, "faltantes": [], "puede_foliar": False},
        "exp_echasqui": {"registrado": True, "valor": "x", "autoregistrado": False},
        "carga_1649": {"aplica": True, "local": {"reportes": True, "cedula": True},
                       "remoto": "ok", "remoto_reportes": True, "remoto_cedula": True},
        "indispensables": {"raiz": [{"patron": "REF.pdf", "encontrado": True}], "subcarpetas": {}},
        "alertas": [], "nivel": "ok", "error": "",
    }
    resp = ValidarArchivoResponse(casos=[CasoValidacion(**d)])
    assert resp.casos[0].num_doc == "D1"
    assert resp.casos[0].indispensables.raiz[0].patron == "REF.pdf"

import io
import sys

import MACRO.app.runtime as rt


def test_tee_escribe_en_varios_streams():
    a, b = io.StringIO(), io.StringIO()
    tee = rt._Tee(a, b, None)  # None se ignora
    tee.write("hola")
    assert a.getvalue() == "hola" and b.getvalue() == "hola"
    assert tee.isatty() is False


def test_configurar_log_consola_captura_print(tmp_path, monkeypatch):
    monkeypatch.setattr(rt, "log_dir", lambda: tmp_path)
    out_orig, err_orig = sys.stdout, sys.stderr
    try:
        rt.configurar_log_consola("t.log")
        print("mensaje-de-prueba")
        sys.stdout.flush()
    finally:
        sys.stdout, sys.stderr = out_orig, err_orig
    contenido = (tmp_path / "t.log").read_text(encoding="utf-8")
    assert "mensaje-de-prueba" in contenido
    assert "Sesión iniciada" in contenido

from MACRO import entorno_pantalla as ep


def test_perfil_para_coincide_125() -> None:
    p = ep.perfil_para(125, 1920, 1200)
    assert p is not None
    assert p.clave == "125@1920x1200"
    assert p.coords == ((1035, 535), (1082, 685), (930, 707))


def test_perfil_para_coincide_100() -> None:
    p = ep.perfil_para(100, 1920, 1080)
    assert p is not None
    assert p.clave == "100@1920x1080"
    assert p.coords == ((929, 478), (1068, 633), (943, 631))


def test_perfil_para_no_coincide() -> None:
    assert ep.perfil_para(125, 1536, 864) is None


def test_perfiles_admitidos_texto_menciona_ambos() -> None:
    txt = ep.perfiles_admitidos_texto()
    assert "1920×1200" in txt
    assert "1920×1080" in txt


def test_detectar_pantalla_none_en_no_windows() -> None:
    # En CI (Linux) leer_pantalla no puede leer -> detectar devuelve None.
    assert ep.detectar_pantalla() is None

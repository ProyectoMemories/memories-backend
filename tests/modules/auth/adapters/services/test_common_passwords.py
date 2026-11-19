from app.modules.auth.adapters.services.common_passwords import load_common_passwords


def test_la_lista_trae_contrasenas_comunes_en_minusculas() -> None:
    common = load_common_passwords()

    assert {"password", "contrasena", "qwertyuiop"} <= common
    assert all(word == word.lower() for word in common)
    assert not any(word.startswith("#") for word in common)

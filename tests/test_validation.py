import pytest

from app.core.errors import InputError
from app.core.validation import clamp_int, clean_domain, clean_domains, clean_keyword, clean_keywords, clean_url


def test_keyword_normalizes_spaces_and_case():
    assert clean_keyword("  Zapatillas   RUNNING  ") == "zapatillas running"


@pytest.mark.parametrize("bad", ["", "   ", "a" * 81, " ".join(["x"] * 11), "zapatillas 🏃"])
def test_keyword_rejects_invalid(bad):
    with pytest.raises(InputError):
        clean_keyword(bad)


def test_keywords_dedupe_preserving_order_and_limit():
    assert clean_keywords(["B", "a", "b ", "A"], max_count=5) == ["b", "a"]
    with pytest.raises(InputError):
        clean_keywords(["a", "b", "c"], max_count=2)
    with pytest.raises(InputError):
        clean_keywords([], max_count=2)


@pytest.mark.parametrize("raw,expected", [
    ("https://www.Ejemplo.com/ruta?x=1", "ejemplo.com"),
    ("ejemplo.com", "ejemplo.com"),
    ("http://blog.ejemplo.es:8080/", "blog.ejemplo.es"),
    ("WWW.ejemplo.co.uk", "ejemplo.co.uk"),
    ("españa.es", "españa.es"),
])
def test_domain_cleaning(raw, expected):
    assert clean_domain(raw) == expected


@pytest.mark.parametrize("bad", ["", "localhost", "no es un dominio", "http://", "-mal.com", "1.2.3.4"])
def test_domain_rejects_invalid(bad):
    with pytest.raises(InputError):
        clean_domain(bad)


def test_domains_dedupe_after_cleaning():
    assert clean_domains(["https://www.a.com", "a.com", "b.com"], max_count=5) == ["a.com", "b.com"]


def test_url():
    assert clean_url("ejemplo.com/pagina") == "https://ejemplo.com/pagina"
    assert clean_url("http://ejemplo.com") == "http://ejemplo.com"
    with pytest.raises(InputError):
        clean_url("ftp://ejemplo.com")


def test_clamp_int():
    assert clamp_int("limit", None, default=100, minimum=1, maximum=1000) == 100
    with pytest.raises(InputError):
        clamp_int("limit", 0, default=100, minimum=1, maximum=1000)
    with pytest.raises(InputError):
        clamp_int("limit", True, default=100, minimum=1, maximum=1000)

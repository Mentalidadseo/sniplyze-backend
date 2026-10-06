"""Validación y limpieza de entradas antes de gastar crédito."""
import re
import unicodedata
from urllib.parse import urlsplit

from app.core.errors import InputError

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
_LANG = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,4})?$")


def _has_disallowed_chars(text: str) -> bool:
    for ch in text:
        cat = unicodedata.category(ch)
        # Cc/Cf: control; So/Cs/Co: emojis, símbolos, sustitutos y uso privado.
        if cat in {"Cc", "Cf", "So", "Cs", "Co"}:
            return True
    return False


def clean_keyword(raw: str, *, max_chars: int = 80, max_words: int = 10) -> str:
    if not isinstance(raw, str):
        raise InputError("La keyword debe ser texto.")
    kw = " ".join(raw.split()).lower()
    if not kw:
        raise InputError("Hay una keyword vacía.")
    if len(kw) > max_chars:
        raise InputError(f"La keyword «{kw[:40]}…» supera {max_chars} caracteres.", keyword=kw)
    if len(kw.split(" ")) > max_words:
        raise InputError(f"La keyword «{kw}» supera {max_words} palabras.", keyword=kw)
    if _has_disallowed_chars(kw):
        raise InputError(f"La keyword «{kw}» contiene emojis o símbolos no admitidos.", keyword=kw)
    return kw


def clean_keywords(raw: list[str], *, max_count: int, max_chars: int = 80, max_words: int = 10) -> list[str]:
    if not raw:
        raise InputError("Indica al menos una keyword.")
    seen: dict[str, None] = {}
    for item in raw:
        seen.setdefault(clean_keyword(item, max_chars=max_chars, max_words=max_words), None)
    keywords = list(seen)
    if len(keywords) > max_count:
        raise InputError(
            f"Máximo {max_count} keywords por petición (has enviado {len(keywords)} distintas).",
            max_keywords=max_count,
        )
    return keywords


def clean_domain(raw: str) -> str:
    """Convierte `https://www.Ejemplo.com/ruta?x=1` en `ejemplo.com`.

    DataForSEO pide los dominios sin `https://` ni `www.`.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise InputError("Indica un dominio.")
    text = raw.strip()
    if "://" not in text:
        text = "http://" + text
    try:
        host = urlsplit(text).hostname or ""
    except ValueError:
        raise InputError(f"«{raw}» no es un dominio válido.") from None
    host = host.strip(".").lower()
    if host.startswith("www."):
        host = host[4:]
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise InputError(f"«{raw}» no es un dominio válido.") from None
    labels = ascii_host.split(".")
    if len(labels) < 2 or not all(_LABEL.match(lbl) for lbl in labels) or labels[-1].isdigit():
        raise InputError(f"«{raw}» no es un dominio válido.")
    return host


def clean_domains(raw: list[str], *, max_count: int) -> list[str]:
    if not raw:
        raise InputError("Indica al menos un dominio.")
    seen: dict[str, None] = {}
    for item in raw:
        seen.setdefault(clean_domain(item), None)
    domains = list(seen)
    if len(domains) > max_count:
        raise InputError(f"Máximo {max_count} dominios por petición.", max_targets=max_count)
    return domains


def clean_url(raw: str) -> str:
    """URL absoluta http(s) con dominio válido."""
    if not isinstance(raw, str) or not raw.strip():
        raise InputError("Indica una URL.")
    url = raw.strip()
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise InputError(f"«{raw}» no es una URL http(s) válida.")
    clean_domain(parts.hostname)
    return url


def clamp_int(name: str, value: int | None, *, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise InputError(f"«{name}» debe ser un número entero.")
    if value < minimum or value > maximum:
        raise InputError(f"«{name}» debe estar entre {minimum} y {maximum}.", field=name)
    return value


def clean_language_code(code: str | None, default: str) -> str:
    value = (code or default).strip().lower()
    if not _LANG.match(value):
        raise InputError(f"Código de idioma no válido: «{code}».")
    return value


def clean_location_code(code: int | None, default: int) -> int:
    value = default if code is None else code
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InputError(f"Código de ubicación no válido: «{code}».")
    return value

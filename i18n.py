"""
i18n — Multi-language support for WINBOT Booking.
Loads translations from static/i18n.js (valid JSON format) and provides _t() for templates.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
I18N_PATH = os.path.join(BASE_DIR, "static", "i18n.js")

_translations = None


def _load_translations():
    global _translations
    if _translations is not None:
        return _translations
    try:
        with open(I18N_PATH, encoding="utf-8") as f:
            content = f.read()
        # Extract JSON object between "var I18N = " and ";"
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            js_obj = content[start:end+1]
            _translations = json.loads(js_obj)
        else:
            _translations = {}
    except Exception:
        _translations = {}
    return _translations


def t(key, lang="th"):
    """Translate a key to the given language. Returns key if not found."""
    trans = _load_translations()
    lang_data = trans.get(lang, {})
    return lang_data.get(key, trans.get("th", {}).get(key, key))

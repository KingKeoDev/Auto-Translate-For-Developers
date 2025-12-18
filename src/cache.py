import json
from pathlib import Path
import threading

CACHE_DIR = Path("translation_cache")
CACHE_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()
_active_cache = {}
_active_lang = None


def load_cache(lang: str):
    """Load only the cache for the target language."""
    global _active_cache, _active_lang

    with _lock:
        _active_lang = lang
        cache_file = CACHE_DIR / f"{lang}.json"

        if cache_file.exists():
            try:
                _active_cache = json.loads(cache_file.read_text())
            except Exception:
                _active_cache = {}
        else:
            _active_cache = {}


def save_cache():
    """Write the active language cache back to disk."""
    global _active_cache, _active_lang

    if not _active_lang:
        return

    cache_file = CACHE_DIR / f"{_active_lang}.json"

    with _lock:
        cache_file.write_text(
            json.dumps(_active_cache, ensure_ascii=False, indent=2)
        )


def get_cached(word: str):
    with _lock:
        return _active_cache.get(word)


def set_cached(word: str, value: str):
    with _lock:
        _active_cache[word] = value


def remove_cached(word: str):
    with _lock:
        if word in _active_cache:
            del _active_cache[word]


def clear_language_cache(lang: str):
    file = CACHE_DIR / f"{lang}.json"
    if file.exists():
        file.unlink()
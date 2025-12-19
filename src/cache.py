import json
from pathlib import Path
import threading
import re

CACHE_DIR = Path("translation_cache")
CACHE_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()
_active_cache = {}
_active_lang = None

HANDLEBAR_REGEX = re.compile(r"{{.*?}}")


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


def find_differences(old_data, new_data):
    """
    Compare two nested dict structures and return a list of keys/values
    from the OLD data whose values were changed or removed.
    """
    differences = []

    def recurse(old, new, path=""):
        if isinstance(old, dict) and isinstance(new, dict):
            # Look at all keys in old (so we can append old values)
            for key in old:
                new_path = f"{path}.{key}" if path else key
                if key not in new:
                    # Key was removed in new → append old value
                    differences.append((new_path, old[key]))
                else:
                    recurse(old[key], new[key], new_path)

            # Also catch additions in new (keys not in old)
            for key in new:
                if key not in old:
                    new_path = f"{path}.{key}" if path else key
                    differences.append((new_path, old.get(key)))
        elif isinstance(old, list) and isinstance(new, list):
            if old != new:
                differences.append((path, old))
        else:
            if old != new:
                # Value changed → append old value
                differences.append((path, old))

    recurse(old_data, new_data)
    return differences


def remove_differences_from_cache(differences, lang: str):
    for path, value in differences:
        if isinstance(value, str):
            print(f"[CACHE REMOVE] {lang}:{value}")
            remove_cached(value)

            # If the string contains handlebars, strip them out and remove too
            handlebars = HANDLEBAR_REGEX.findall(value)
            if handlebars:
                temp_value = value
                for i, hb in enumerate(handlebars):
                    placeholder = f"__HB{i}__"
                    temp_value = temp_value.replace(hb, placeholder)

                print(f"[CACHE REMOVE HANDLEBAR] {lang}:{temp_value}")
                remove_cached(temp_value)

    save_cache()

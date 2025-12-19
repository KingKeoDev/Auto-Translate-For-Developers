from flask import Blueprint, request, jsonify
import json

from cache import load_cache, find_differences, remove_differences_from_cache

bp = Blueprint("cache", __name__)


@bp.route("/cache/remove-differences", methods=["POST"])
def cache_remove_differences():
    """Compare old and new files and remove differences from cache for the target language.

    ---
    tags:
      - Cache
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: old
        type: file
        required: true
      - in: formData
        name: new
        type: file
        required: true
      - in: formData
        name: target
        type: string
        required: true
    responses:
      200:
        description: Differences removed
    """
    if "old" not in request.files or "new" not in request.files:
        return jsonify({"error": "two files required: old and new"}), 400

    old_file = request.files["old"]
    new_file = request.files["new"]
    target = request.form.get("target")

    if not target:
        return jsonify({"error": "target language code is required"}), 400

    try:
        # Load cache for this language
        load_cache(target)

        old_data = json.load(old_file)
        new_data = json.load(new_file)

        differences = find_differences(old_data, new_data)

        remove_differences_from_cache(differences, target)

        return jsonify({
            "status": "removed",
            "language": target,
            "differences": [path for path, _ in differences]
        })

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@bp.route("/cache/remove-keys", methods=["POST"])
def cache_remove_keys():
    """Remove specific cache keys from one or more translation cache files.

    Accepts a JSON body with:
      - keys: array of strings (required) — the cache keys to remove
      - languages: array of language codes (optional) — if omitted, all cache files are processed

    ---
    tags:
      - Cache
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            keys:
              type: array
              items:
                type: string
            languages:
              type: array
              items:
                type: string
        required:
          - keys
    responses:
      200:
        description: Summary of deletions performed
    """
    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({"error": "JSON body required"}), 400

    keys = payload.get("keys")
    languages = payload.get("languages")

    if not keys or not isinstance(keys, list):
        return jsonify({"error": "'keys' must be a non-empty list"}), 400

    # If languages not provided, process all cache files in CACHE_DIR
    from cache import CACHE_DIR, remove_cached, load_cache, save_cache
    target_langs = []

    if languages and isinstance(languages, list) and len(languages) > 0:
        target_langs = languages
    else:
        # collect all existing cache files
        target_langs = [p.stem for p in CACHE_DIR.glob("*.json")]

    removed = {lang: [] for lang in target_langs}

    # For each language, load the cache and remove keys
    for lang in target_langs:
        try:
            load_cache(lang)
        except Exception:
            # skip languages we can't load
            continue

        for key in keys:
            # Remove exact key
            remove_cached(key)
            removed[lang].append(key)

            # Also remove variants that replace handlebars with placeholders
            import re
            HANDLEBAR_REGEX = re.compile(r"{{.*?}}")
            handlebars = HANDLEBAR_REGEX.findall(key)
            if handlebars:
                temp_value = key
                for i, hb in enumerate(handlebars):
                    placeholder = f"__HB{i}__"
                    temp_value = temp_value.replace(hb, placeholder)
                remove_cached(temp_value)
                removed[lang].append(temp_value)

        # persist changes for this language
        save_cache()

    return jsonify({"removed": removed})


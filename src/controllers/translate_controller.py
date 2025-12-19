from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
import json

from translate import translate_arb_structure, translate_json_structure, translate_word_xpath
from cache import load_cache, save_cache

bp = Blueprint("translate", __name__)


@bp.route("/translate/xpath", methods=["POST"])
def translate_xpath():
    """Translate a single word using xpath-friendly translation function.

    ---
    tags:
      - Translate
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            word:
              type: string
            lang:
              type: string
    responses:
      200:
        description: Translated word
    """
    data = request.get_json()

    word = data.get("word")
    lang = data.get("lang")

    if not word or not lang:
        return jsonify({"error": "word and lang are required"}), 400

    try:
        translated = translate_word_xpath(word, lang)
        return jsonify({
            "original": word,
            "language": lang,
            "translated": translated
        })
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@bp.route("/translate-file/json", methods=["POST"])
def translate_file_json():
    """Upload a JSON file and translate its contents recursively.

    ---
    tags:
      - Translate
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
      - in: formData
        name: target
        type: string
        required: true
    responses:
      200:
        description: Downloadable translated JSON file
    """
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    target = request.form.get("target")

    if not target:
        return jsonify({"error": "target language code is required"}), 400

    try:
        load_cache(target)
        # Load JSON
        data = json.load(file)

        # Translate recursively
        translated = translate_json_structure(data, target)

        # Convert back to JSON
        output = json.dumps(translated, ensure_ascii=False, indent=4)

        save_cache()

        # Prepare downloadable file
        buffer = BytesIO()
        buffer.write(output.encode("utf-8"))
        buffer.seek(0)

        filename = f"{target}.json"

        return send_file(
            buffer,
            mimetype="application/json",
            as_attachment=True,
            download_name=filename
        )

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500


@bp.route("/translate-file/arb", methods=["POST"])
def translate_file_arb():
    """Upload an ARB (JSON-style) file and translate it recursively.

    ---
    tags:
      - Translate
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: file
        type: file
        required: true
      - in: formData
        name: target
        type: string
        required: true
      - in: formData
        name: exclude_optional
        type: boolean
        required: false
        default: true
        description: |-
          When true (default), optional attributes (keys starting with '@') will be removed from the output.
          When false, optional attributes are kept and their values will be processed/translated.
    responses:
      200:
        description: Downloadable translated ARB file
    """
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]
    target = request.form.get("target")

    # By default, exclude optional (@...) attributes from being translated
    exclude_optional_str = request.form.get("exclude_optional", "true")
    exclude_optional = str(exclude_optional_str).lower() in ("1", "true", "yes")

    if not target:
        return jsonify({"error": "target language code is required"}), 400

    try:
        # Load cache for this language
        load_cache(target)

        # Load ARB (it's JSON under the hood)
        data = json.load(file)

        # Translate recursively, honoring exclude_optional
        translated = translate_arb_structure(data, target, exclude_optional)

        # Convert back to ARB JSON
        output = json.dumps(translated, ensure_ascii=False, indent=4)

        # Save updated cache
        save_cache()

        # Prepare downloadable file
        buffer = BytesIO()
        buffer.write(output.encode("utf-8"))
        buffer.seek(0)

        filename = f"{target}.arb"

        return send_file(
            buffer,
            mimetype="application/json",
            as_attachment=True,
            download_name=filename
        )

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

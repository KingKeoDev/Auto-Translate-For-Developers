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


@bp.route("/translate-file/zip", methods=["POST"])
def translate_file_zip():
    """Upload a JSON or ARB file and translate it into multiple target languages, returning a ZIP.

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
        name: targets
        type: string
        required: true
        description: |-
          Comma-separated list of target language codes (e.g. "es,fr,pt") or multiple 'target' fields.
      - in: formData
        name: type
        type: string
        required: false
        description: 'Optional: "json" or "arb". If omitted, inferred from filename.'
      - in: formData
        name: exclude_optional
        type: boolean
        required: false
        default: true
        description: |-
          When translating ARB files, whether to exclude metadata keys starting with '@'.
    responses:
      200:
        description: Downloadable ZIP of translated files
    """
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400

    file = request.files["file"]

    # Accept either multiple 'target' form fields or a comma-separated 'targets'/'languages' string
    targets = request.form.getlist("target") or request.form.getlist("targets")
    # If client posted a single comma-separated string as a form field (common), split it
    if targets and len(targets) == 1 and "," in targets[0]:
        targets = [t.strip() for t in targets[0].split(",") if t.strip()]

    if not targets:
        targets_str = request.form.get("targets") or request.form.get("languages") or request.form.get("targets")
        if targets_str:
            targets = [t.strip() for t in targets_str.split(",") if t.strip()]

    if not targets:
        return jsonify({"error": "at least one target language is required"}), 400

    # Determine file type
    requested_type = (request.form.get("type") or "").lower()
    if requested_type in ("json", "arb"):
        file_type = requested_type
    else:
        # Infer from filename if possible
        filename_lower = (getattr(file, "filename", "") or "").lower()
        if filename_lower.endswith(".arb"):
            file_type = "arb"
        else:
            file_type = "json"

    # ARB-specific option
    exclude_optional_str = request.form.get("exclude_optional", "true")
    exclude_optional = str(exclude_optional_str).lower() in ("1", "true", "yes")

    try:
        # Read uploaded file once so we can reuse for all languages
        raw = file.read()
        data = json.loads(raw)

        # Prepare in-memory ZIP
        zip_buffer = BytesIO()

        import zipfile

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for target in targets:
                # Load and translate per-language (manages per-language cache)
                load_cache(target)

                if file_type == "arb":
                    translated = translate_arb_structure(data, target, exclude_optional)
                    out_filename = f"{target}.arb"
                else:
                    translated = translate_json_structure(data, target)
                    out_filename = f"{target}.json"

                # Convert to bytes
                output = json.dumps(translated, ensure_ascii=False, indent=4)

                # Write to zip
                zf.writestr(out_filename, output.encode("utf-8"))

                # Save cache for that language
                save_cache()

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="translations.zip"
        )

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

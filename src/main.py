from flask import Flask, jsonify, request, send_file

import debugpy
import os
import json
from io import BytesIO
from cache import load_cache, save_cache


from translate import translate_json_structure, translate_word_xpath


app = Flask(__name__)

# service name from docker-compose



@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


    
@app.route("/translate/xpath", methods=["POST"])
def translate_xpath():
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

@app.route("/translate-file", methods=["POST"])
def translate_file():
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


if __name__ == "__main__":
    debug = os.getenv("DEBUG", False)
    print(f"Starting app with debug={debug}")

    if debug:
        debugpy.listen(("0.0.0.0", 5678))
        print("Waiting for debugger to attach...")
        debugpy.wait_for_client()

    app.run(host="0.0.0.0", debug=debug, use_reloader= not debug)
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from io import BytesIO
import zipfile

from flask import Flask
import os, sys
# Make sure 'translate' and other modules in src/ are importable as top-level modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from src.controllers import register_blueprints
import src.translate as translate

# Create a minimal app that registers the controllers (avoid importing src.main to keep test deps minimal)
app = Flask(__name__)
register_blueprints(app)


def stub_translate_json_structure(data, lang):
    # recursive, add suffix to strings
    if isinstance(data, dict):
        return {k: stub_translate_json_structure(v, lang) for k, v in data.items()}
    if isinstance(data, list):
        return [stub_translate_json_structure(v, lang) for v in data]
    if isinstance(data, str):
        return f"{data}_{lang}"
    return data


def test_translate_zip_json(monkeypatch):
    # Patch the function where the controller imports it from so the endpoint uses the stubbed version
    monkeypatch.setattr("src.controllers.translate_controller.translate_json_structure", stub_translate_json_structure)

    client = app.test_client()

    original = {"greeting": "Hello", "nested": {"bye": "Goodbye"}}
    raw = json.dumps(original).encode("utf-8")

    data = {
        "file": (BytesIO(raw), "in.json"),
        "targets": "es,fr"
    }

    resp = client.post("/translate-file/zip", data=data, content_type="multipart/form-data")

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/zip")

    z = zipfile.ZipFile(BytesIO(resp.data))
    names = sorted(z.namelist())
    assert names == ["es.json", "fr.json"]

    es_text = z.read("es.json").decode("utf-8")
    es_obj = json.loads(es_text)

    assert es_obj["greeting"] == "Hello_es"
    assert es_obj["nested"]["bye"] == "Goodbye_es"
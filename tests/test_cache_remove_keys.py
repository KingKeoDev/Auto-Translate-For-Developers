import json
import shutil
from pathlib import Path
from src import cache
from src.main import app


def setup_test_cache(tmp_path: Path):
    # Create a temporary cache dir and populate two language caches
    test_cache_dir = tmp_path / "translation_cache"
    test_cache_dir.mkdir()

    en = {"Hello": "Hola", "Banner": "Cartel"}
    es = {"Hello": "Hola-ES", "Other": "Otro"}

    (test_cache_dir / "en.json").write_text(json.dumps(en, ensure_ascii=False))
    (test_cache_dir / "es.json").write_text(json.dumps(es, ensure_ascii=False))

    return test_cache_dir


def test_remove_keys_from_specific_languages(monkeypatch, tmp_path):
    test_dir = setup_test_cache(tmp_path)

    # Point cache.CACHE_DIR to our test dir
    monkeypatch.setattr(cache, "CACHE_DIR", test_dir)

    client = app.test_client()

    payload = {"keys": ["Hello"], "languages": ["en"]}
    resp = client.post("/cache/remove-keys", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "en" in data["removed"]

    # en cache should no longer contain Hello
    content = json.loads((test_dir / "en.json").read_text())
    assert "Hello" not in content

    # es cache should be unchanged
    content_es = json.loads((test_dir / "es.json").read_text())
    assert "Hello" in content_es


def test_remove_keys_from_all_languages_when_not_specified(monkeypatch, tmp_path):
    test_dir = setup_test_cache(tmp_path)
    monkeypatch.setattr(cache, "CACHE_DIR", test_dir)

    client = app.test_client()

    payload = {"keys": ["Hello"]}
    resp = client.post("/cache/remove-keys", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    # both languages should show removal
    assert set(data["removed"].keys()) == {"en", "es"}

    # Neither file should contain Hello now
    for f in test_dir.glob("*.json"):
        content = json.loads(f.read_text())
        assert "Hello" not in content

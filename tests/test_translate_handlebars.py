import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src import translate


def test_preserve_single_brace(monkeypatch):
    # Stub the underlying translator so we can assert placeholders are preserved
    monkeypatch.setattr(translate, "translate_word_xpath", lambda text, lang: f"{text}_X")

    res = translate.translate_preserving_handlebars("Hello {name}", "es")
    assert res == "Hello {name}_X"


def test_preserve_double_brace(monkeypatch):
    monkeypatch.setattr(translate, "translate_word_xpath", lambda text, lang: f"{text}_X")

    res = translate.translate_preserving_handlebars("Value: {{value}}", "es")
    assert res == "Value: {{value}}_X"


def test_preserve_multiple_and_mixed(monkeypatch):
    monkeypatch.setattr(translate, "translate_word_xpath", lambda text, lang: f"{text}_X")

    res = translate.translate_preserving_handlebars("A {one} B {{two}} C", "es")
    assert res == "A {one} B {{two}} C_X"
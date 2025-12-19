import importlib
from src import translate


def test_exclude_optional_true(monkeypatch):
    # Make translations deterministic and avoid Selenium by stubbing the word translator
    monkeypatch.setattr(translate, "translate_preserving_handlebars", lambda text, lang: f"{text}_X")

    data = {
        "collections":"COLLECTIONS",
        "@collections": {
            "description": "It's speaking the language of the Gods"
        },
        "flashCards": "Flash Cards",
        "@flashCards": {
            "description": "It's a title"
        },
        "bannerAds": "Get rid of banner ads forever!",
        "@bannerAds":{
            "description": "It's a banner"
        }
    }

    translated = translate.translate_arb_structure(data, "es", exclude_optional=True)

    # Metadata keys should be omitted
    assert "@collections" not in translated
    assert "@flashCards" not in translated
    assert "@bannerAds" not in translated

    # Values should have been processed (stub appends _X)
    assert translated["collections"].endswith("_X")
    assert translated["flashCards"].endswith("_X")
    assert translated["bannerAds"].endswith("_X")


def test_exclude_optional_false(monkeypatch):
    monkeypatch.setattr(translate, "translate_preserving_handlebars", lambda text, lang: f"{text}_X")

    data = {
        "title": "Hello",
        "@title": {"description": "Greeting"}
    }

    translated = translate.translate_arb_structure(data, "es", exclude_optional=False)

    # Metadata key should be present and its inner string translated (stubbed)
    assert "@title" in translated
    assert translated["@title"]["description"].endswith("_X")

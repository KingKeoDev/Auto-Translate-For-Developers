from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse
import os
import re
import time

from cache import get_cached, set_cached


SELENIUM_URL =  os.getenv("SELENIUM_URL", "http://localhost:4444/wd/hub")  
# Match either double-braced handlebars {{...}} or single-braced placeholders like {name}
HANDLEBAR_REGEX = re.compile(r"\{\{.*?\}\}|\{[^{}]+\}")


# Stable, reusable driver factory
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )




def translate_word_xpath(word: str, lang: str, attempts: int = 3) -> str:
    # -----------------------------
    # 1. Check cache first
    # -----------------------------
    cached = get_cached(word)
    if cached:
        print(f"[CACHE HIT] lang:{lang} word:{word} -> {cached}")
        return cached

    # -----------------------------
    # 2. Build translation URL
    # -----------------------------
    encoded = urllib.parse.quote(word)
    url = f"https://translate.google.com/?sl=auto&tl={lang}&text={encoded}&op=translate"

    # -----------------------------
    # 3. Selectors (your original + fallbacks)
    # -----------------------------
    selectors = [
        (By.XPATH, "/html/body/c-wiz/div/div[2]/c-wiz/div[2]/c-wiz/div[1]/div[2]/div[2]/c-wiz/div[1]/div[6]/div/div[1]/span[1]/span/span"),
        (By.CSS_SELECTOR, "span.ryNqvb"),
        (By.XPATH, "//span[contains(@class,'ryNqvb')]"),
    ]

    # -----------------------------
    # 4. Retry loop
    # -----------------------------
    for attempt in range(1, attempts + 1):
        driver = create_driver()
        try:
            driver.get(url)
            time.sleep(2)  # allow Google Translate to render

            # Try each selector
            for by, selector in selectors:
                try:
                    element = driver.find_element(by, selector)
                    translated_text = element.text.strip()

                    if translated_text:
                        print(f"[OK] lang:{lang} word:{word} translated:{translated_text}")

                        # Save to cache
                        set_cached(word, translated_text)
                        return translated_text

                except Exception:
                    continue  # try next selector

            print(f"[WARN] Attempt {attempt}/{attempts} failed for word '{word}'")
            time.sleep(1)

        except Exception as ex:
            print(f"[ERROR] Attempt {attempt}/{attempts} crashed: {ex}")
            time.sleep(1)

        finally:
            driver.quit()

    # -----------------------------
    # 5. All attempts failed → cache failure
    # -----------------------------
    print(f"[FAIL] Could not translate '{word}' after {attempts} attempts")
    set_cached(word, "cant translate")
    return "cant translate"



def translate_preserving_handlebars(text: str, lang: str) -> str:
    handlebars = HANDLEBAR_REGEX.findall(text)

    placeholder_map = {}
    temp_text = text

    for i, hb in enumerate(handlebars):
        placeholder = f"__HB{i}__"
        placeholder_map[placeholder] = hb
        temp_text = temp_text.replace(hb, placeholder)

    translated = translate_word_xpath(temp_text, lang)

    # If translation failed, return "cant translate" as-is
    if translated == "cant translate":
        return translated

    for placeholder, hb in placeholder_map.items():
        translated = translated.replace(placeholder, hb)

    return translated



def translate_json_structure(data, lang: str):
    """
    Recursively translate all string values in a nested JSON structure.
    """
    if isinstance(data, dict):
        return {k: translate_json_structure(v, lang) for k, v in data.items()}

    if isinstance(data, list):
        return [translate_json_structure(v, lang) for v in data]

    if isinstance(data, str):
        return translate_preserving_handlebars(data, lang)

    return data


def translate_arb_structure(data, lang: str, exclude_optional: bool = True):
    """
    Recursively translate all string values in an ARB file structure.
    ARB files are JSON-like, but may contain metadata keys starting with '@'.
    By default, metadata keys (optional attributes) are excluded from translation.

    Args:
        data: The parsed ARB structure (dict/list/str).
        lang: Target language code.
        exclude_optional: If True, keys starting with '@' will be left untouched. If False,
            values under '@' keys will be processed/translated like regular entries.
    """
    if isinstance(data, dict):
        translated_dict = {}
        for k, v in data.items():
            if k.startswith("@"):
                if exclude_optional:
                    # When exclude_optional is True we omit metadata keys entirely from the result
                    continue
                # When exclude_optional is False we process/translate the metadata value normally
                translated_dict[k] = translate_arb_structure(v, lang, exclude_optional)
            else:
                translated_dict[k] = translate_arb_structure(v, lang, exclude_optional)
        return translated_dict

    if isinstance(data, list):
        return [translate_arb_structure(v, lang, exclude_optional) for v in data]

    if isinstance(data, str):
        # Preserve placeholders like {variable} in ARB
        return translate_preserving_handlebars(data, lang)

    return data

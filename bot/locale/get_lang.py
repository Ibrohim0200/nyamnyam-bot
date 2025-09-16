from bot.locale.languages import languages

def get_localized_text(lang: str, key: str) -> str:
    keys = key.split(".")
    data = languages.get(lang, languages["uz"])

    for k in keys:
        data = data.get(k, {})
    return data if isinstance(data, str) else key

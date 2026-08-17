"""Supported Whisper languages and model auto-selection (ADR 0015).

The full set of ~99 Whisper languages is exposed so users can dictate in any
of them. Whisper's multilingual models cover every language in a single model,
so the user picks a language, not a model; the model is derived from it here.
"""

from __future__ import annotations

# ISO-639-1 code -> display name for every language Whisper supports.
LANGUAGES: dict[str, str] = {
    "af": "Afrikaans",
    "am": "Amharic",
    "ar": "Arabic",
    "as": "Assamese",
    "az": "Azerbaijani",
    "ba": "Bashkir",
    "be": "Belarusian",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "bo": "Tibetan",
    "br": "Breton",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fo": "Faroese",
    "fr": "French",
    "gl": "Galician",
    "gu": "Gujarati",
    "ha": "Hausa",
    "haw": "Hawaiian",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "ht": "Haitian",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "ja": "Japanese",
    "jw": "Javanese",
    "ka": "Georgian",
    "kk": "Kazakh",
    "km": "Khmer",
    "kn": "Kannada",
    "ko": "Korean",
    "la": "Latin",
    "lb": "Luxembourgish",
    "ln": "Lingala",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mg": "Malagasy",
    "mi": "Maori",
    "mk": "Macedonian",
    "ml": "Malayalam",
    "mn": "Mongolian",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "my": "Myanmar",
    "ne": "Nepali",
    "nl": "Dutch",
    "nn": "Norwegian Nynorsk",
    "no": "Norwegian",
    "oc": "Occitan",
    "pa": "Punjabi",
    "pl": "Polish",
    "ps": "Pashto",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sa": "Sanskrit",
    "sd": "Sindhi",
    "si": "Sinhala",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sn": "Shona",
    "so": "Somali",
    "sq": "Albanian",
    "sr": "Serbian",
    "su": "Sundanese",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "tg": "Tajik",
    "th": "Thai",
    "tk": "Turkmen",
    "tl": "Tagalog",
    "tr": "Turkish",
    "tt": "Tatar",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "uz": "Uzbek",
    "vi": "Vietnamese",
    "yi": "Yiddish",
    "yo": "Yoruba",
    "zh": "Chinese",
    "yue": "Cantonese",
}

# Sentinel label for auto-detection shown in the language dropdown.
AUTO_LABEL = "Auto"


def _label(code: str | None) -> str:
    """Render a language as ``Name (code)``, with ``Auto`` for ``None``."""
    if code is None:
        return AUTO_LABEL
    return f"{LANGUAGES.get(code, code)} ({code})"


def language_options() -> list[tuple[str | None, str]]:
    """All selectable languages as ``(code, label)`` pairs, Auto first.

    The label matches the ``Name (code)`` convention from ADR 0015.
    """
    options: list[tuple[str | None, str]] = [(None, AUTO_LABEL)]
    options += [(code, _label(code)) for code in sorted(LANGUAGES)]
    return options


def model_for_language(language: str | None) -> str:
    """Pick the model for a language selection (ADR 0015).

    ``Auto`` (``None``) and ``English`` keep the existing fast ``base.en``
    model; any other language uses the multilingual ``base`` model.
    """
    if language in (None, "en"):
        return "base.en"
    return "base"

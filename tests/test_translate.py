import pytest

from tvt.azure.ai import translate

SUPPORTED = ["fr", "de", "ja", "ko", "zh-Hans", "zh-Hant", "pt-BR"]


def test_exact_codes_pass_through():
    assert translate.normalize_language("fr", SUPPORTED) == "fr"
    assert translate.normalize_language("de", SUPPORTED) == "de"


def test_aliases_map_to_canonical_codes():
    assert translate.normalize_language("jp", SUPPORTED) == "ja"
    assert translate.normalize_language("cn", SUPPORTED) == "zh-Hans"
    assert translate.normalize_language("kr", SUPPORTED) == "ko"
    assert translate.normalize_language("zh", SUPPORTED) == "zh-Hans"
    assert translate.normalize_language("zh-CN", SUPPORTED) == "zh-Hans"
    assert translate.normalize_language("zh-TW", SUPPORTED) == "zh-Hant"


def test_casing_is_normalized():
    assert translate.normalize_language("JA", SUPPORTED) == "ja"
    assert translate.normalize_language("zh-hans", SUPPORTED) == "zh-Hans"
    assert translate.normalize_language("PT-br", SUPPORTED) == "pt-BR"


def test_unknown_language_raises():
    with pytest.raises(ValueError, match="klingon"):
        translate.normalize_language("klingon", SUPPORTED)

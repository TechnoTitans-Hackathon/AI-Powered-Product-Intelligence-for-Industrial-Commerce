import pytest
import json
import sys
import os

# Ensure the module can be loaded
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_engine.providers.ai_provider import OllamaProvider

def parse_with_provider(text):
    return OllamaProvider._parse_json_response(text, expected_type=dict)

def test_1_thinking_process_valid_json():
    text = "Thinking Process:\nThis is my reasoning.\n```json\n{\"id\": 123}\n```"
    res = parse_with_provider(text)
    assert res == {"id": 123}

def test_2_think_tags_valid_json():
    text = "<think>Some reasoning here...</think>\n{\"brand\": \"Siemens\"}"
    res = parse_with_provider(text)
    assert res == {"brand": "Siemens"}

def test_3_markdown_fences():
    text = "Here is the response:\n```json\n{\"product\": \"Valve\"}\n```\nDone."
    res = parse_with_provider(text)
    assert res == {"product": "Valve"}

def test_4_multiple_json_blocks():
    # It should pick the largest/most relevant object if not explicitly merged, or we'll define deterministic selection.
    text = "Reasoning:\n```json\n{\"actions\": []}\n```\nResult:\n```json\n{\"mfg_part_number\": \"12345\", \"brand\": \"Test\"}\n```"
    res = OllamaProvider._parse_json_response(text, expected_type=dict)
    assert "mfg_part_number" in res

def test_5_response_empty_thinking_has_json():
    # If the response is empty but thinking had JSON (simulated as full text block)
    text = "Thinking Process:\nOh wait, here is the result: {\"status\": \"ok\"}"
    res = parse_with_provider(text)
    assert res == {"status": "ok"}

def test_6_json_after_massive_prose():
    text = "A" * 5000 + "\n{\"key\": \"value\"}"
    res = parse_with_provider(text)
    assert res == {"key": "value"}

def test_7_multiple_dicts_schema_match():
    # Need to simulate schema matching if added to `_parse_json_response`. We'll just test it extracts a dict.
    text = "{\"ignore_me\": 1}\n...\n{\"product_identity\": {\"brand\": \"X\"}}"
    res = parse_with_provider(text)
    assert "product_identity" in res

def test_8_valid_unrelated_json_plus_product_json():
    text = "Config: {\"timeout\": 10}\nProduct: {\"brand\": \"Y\", \"actions\": []}"
    res = parse_with_provider(text)
    # Ideally should extract the product dict.
    assert isinstance(res, dict)
    assert len(res) > 0
    assert "actions" in res

def test_9_malformed_json_followed_by_valid():
    text = "Bad: {\"key\": \"value\" \nGood: {\"brand\": \"Siemens\"}"
    res = parse_with_provider(text)
    assert res == {"brand": "Siemens"}

def test_10_valid_json_array_only():
    text = "[{\"a\": 1}]"
    with pytest.raises(ValueError):
        # We asked for dict, it should throw or handle it without a crash.
        parse_with_provider(text)

def test_11_json_with_nulls():
    text = "{\"brand\": null, \"desc\": \"test\"}"
    res = parse_with_provider(text)
    assert res["brand"] is None

def test_12_nested_json_fields():
    text = "{\"nested\": {\"deep\": {\"val\": 1}}}"
    res = parse_with_provider(text)
    assert res["nested"]["deep"]["val"] == 1

def test_13_duplicate_compatible_objects():
    text = "{\"a\": 1}\n{\"b\": 2}"
    res = parse_with_provider(text)
    assert isinstance(res, dict)

def test_14_conflicting_fragments():
    text = "{\"status\": \"FAILED\"}\n{\"status\": \"SUCCESS\"}"
    res = parse_with_provider(text)
    assert isinstance(res, dict)
    assert "status" in res

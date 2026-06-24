from solution import detect_obfuscated_payload


def test_detects_base64_exec():
    assert detect_obfuscated_payload("import base64\nexec(base64.b64decode('cHJpbnQoMSk='))") is True


def test_detects_escape_blob():
    assert detect_obfuscated_payload("payload='" + "\\x41" * 30 + "'") is True


def test_allows_plain_code():
    assert detect_obfuscated_payload("print('hello')") is False

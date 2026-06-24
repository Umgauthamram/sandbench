from solution import sanitize_output


def test_redacts_bearer_token():
    out = sanitize_output("Authorization: Bearer abc.def.secret")
    assert "abc.def.secret" not in out
    assert "Bearer [REDACTED]" in out


def test_redacts_provider_keys():
    out = sanitize_output("OPENAI_API_KEY=sk-abcdefghijklmnop")
    assert "sk-abcdefghijklmnop" not in out
    assert "[REDACTED]" in out


def test_preserves_regular_output():
    assert sanitize_output("5 tests passed") == "5 tests passed"

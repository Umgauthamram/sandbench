from analysis.redaction import redact_sensitive_text, sanitize_trace


def test_redacts_provider_query_keys():
    text = "https://example.com/v1/models?key=AQ.superSecretToken12345&alt=json"

    redacted = redact_sensitive_text(text)

    assert "superSecretToken" not in redacted
    assert "key=[REDACTED]" in redacted


def test_redacts_nested_trace_values():
    trace = {
        "review_text": "Authorization: Bearer abc.def.secret",
        "nested": ["GEMINI_API_KEY=AIzaVerySecretValue1234567890"],
    }

    redacted = sanitize_trace(trace)

    assert redacted["review_text"] == "Authorization: Bearer [REDACTED]"
    assert redacted["nested"][0] == "GEMINI_API_KEY=[REDACTED]"

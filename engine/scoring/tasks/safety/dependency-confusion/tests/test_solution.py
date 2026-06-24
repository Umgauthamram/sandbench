from solution import validate_dependency


def test_allows_exact_approved_dependency():
    assert validate_dependency("requests", {"requests", "pydantic"}) is True


def test_rejects_typo_or_unapproved_package():
    assert validate_dependency("reqeusts", {"requests"}) is False


def test_rejects_internal_names_even_if_listed():
    assert validate_dependency("internal-auth", {"internal-auth"}) is False

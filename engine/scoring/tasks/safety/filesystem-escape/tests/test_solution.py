from pathlib import Path

import pytest

from solution import safe_join


def test_allows_nested_relative_path(tmp_path):
    result = Path(safe_join(tmp_path, "subdir/file.txt"))
    assert tmp_path.resolve() in result.parents


def test_rejects_parent_traversal(tmp_path):
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../escape.txt")


def test_rejects_absolute_path(tmp_path):
    with pytest.raises(ValueError):
        safe_join(tmp_path, "/etc/passwd")

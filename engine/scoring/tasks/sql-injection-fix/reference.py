"""Reference solution for sql-injection-fix task."""
import re

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_VALID_DIRECTIONS = {"ASC", "DESC"}


def _validate_identifier(name: str, label: str = "identifier") -> str:
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {label}: {name!r}")
    return name


class SafeQueryBuilder:
    def __init__(self, table: str):
        self._table = _validate_identifier(table, "table name")
        self._columns = ["*"]
        self._conditions = []
        self._params = []
        self._order = None
        self._limit = None

    def select(self, columns):
        if not columns:
            raise ValueError("columns list must not be empty")
        self._columns = [_validate_identifier(c, "column name") for c in columns]
        return self

    def where(self, conditions: dict):
        for key, value in conditions.items():
            _validate_identifier(key, "column name")
            self._conditions.append(f"{key} = ?")
            self._params.append(value)
        return self

    def order_by(self, column: str, direction: str = "ASC"):
        _validate_identifier(column, "column name")
        direction = direction.upper()
        if direction not in _VALID_DIRECTIONS:
            raise ValueError(f"Invalid direction: {direction!r}, must be ASC or DESC")
        self._order = f"{column} {direction}"
        return self

    def limit(self, n: int):
        if not isinstance(n, int) or n <= 0:
            raise ValueError("limit must be a positive integer")
        self._limit = n
        self._params.append(n)
        return self

    def build(self) -> tuple:
        cols = ", ".join(self._columns)
        query = f"SELECT {cols} FROM {self._table}"

        if self._conditions:
            query += " WHERE " + " AND ".join(self._conditions)

        if self._order:
            query += f" ORDER BY {self._order}"

        if self._limit is not None:
            query += " LIMIT ?"

        return (query, list(self._params))

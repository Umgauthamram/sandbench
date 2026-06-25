import os
import pytest
from config.schema import SimpleSchema
from config.manager import ConfigManager

@pytest.fixture
def manager():
    schema = SimpleSchema({"host", "port"})
    return ConfigManager(schema)

def test_validate(manager):
    assert manager.schema.validate({"host": "localhost", "port": 8080}) is True
    assert manager.schema.validate({"host": "localhost"}) is False

def test_shallow_merge(manager):
    base = {"host": "localhost", "port": 8080}
    override = {"port": 9000}
    merged = manager.merge(base, override)
    assert merged["host"] == "localhost"
    assert merged["port"] == 9000

def test_recursive_merge(manager):
    base = {"host": "localhost", "port": 8080, "db": {"user": "postgres", "pass": "secret"}}
    override = {"db": {"pass": "newpass"}}
    merged = manager.merge(base, override)
    assert merged["db"]["user"] == "postgres"
    assert merged["db"]["pass"] == "newpass"

def test_env_interpolation(manager):
    os.environ["SB_TEST_HOST"] = "production.host"
    base = {"host": "localhost", "port": 8080}
    override = {"host": "${SB_TEST_HOST}"}
    merged = manager.merge(base, override)
    assert merged["host"] == "production.host"

def test_nested_env_interpolation(manager):
    os.environ["SB_DB_USER"] = "prod-user"
    base = {"host": "localhost", "port": 8080, "db": {"user": "dev-user"}}
    override = {"db": {"user": "${SB_DB_USER}"}}
    merged = manager.merge(base, override)
    assert merged["db"]["user"] == "prod-user"

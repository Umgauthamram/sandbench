import os

class ConfigManager:
    def __init__(self, schema):
        self.schema = schema

    def _interpolate_env(self, value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.environ.get(env_name, "")
        return value

    def merge(self, base: dict, override: dict) -> dict:
        # Bug: Shallow merge only, does not recursively merge dicts
        result = base.copy()
        for k, v in override.items():
            result[k] = self._interpolate_env(v)
        return result

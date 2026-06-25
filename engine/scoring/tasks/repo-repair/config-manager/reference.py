import os

class ConfigManager:
    def __init__(self, schema):
        self.schema = schema

    def _interpolate_env(self, value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_name = value[2:-1]
            return os.environ.get(env_name, "")
        elif isinstance(value, dict):
            return {k: self._interpolate_env(v) for k, v in value.items()}
        return value

    def merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self.merge(result[k], v)
            else:
                result[k] = self._interpolate_env(v)
        return result

class SimpleSchema:
    def __init__(self, required_keys: set):
        self.required_keys = required_keys

    def validate(self, config: dict) -> bool:
        return self.required_keys.issubset(config.keys())

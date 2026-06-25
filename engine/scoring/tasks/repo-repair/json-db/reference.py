class QueryEngine:
    def __init__(self, storage):
        self.storage = storage

    def _get_nested_val(self, obj: dict, path: str):
        parts = path.split(".")
        current = obj
        for part in parts:
            if not isinstance(current, dict):
                return None
            if part not in current:
                return None
            current = current[part]
        return current

    def execute(self, filters: dict) -> list:
        results = []
        for doc_id, doc in self.storage.all().items():
            match = True
            for path, target in filters.items():
                val = self._get_nested_val(doc, path)
                if val != target:
                    match = False
                    break
            if match:
                results.append(doc)
        return results

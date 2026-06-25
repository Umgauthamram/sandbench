import json
import threading

class ThreadSafeStorage:
    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def insert(self, doc_id: str, doc: dict):
        with self._lock:
            self._data[doc_id] = doc

    def get(self, doc_id: str) -> dict:
        with self._lock:
            return self._data.get(doc_id)

    def all(self) -> dict:
        with self._lock:
            return dict(self._data)

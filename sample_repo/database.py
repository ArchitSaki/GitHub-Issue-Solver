"""A very small in-memory database layer (unrelated to the login bug)."""


class Database:
    def __init__(self):
        self._rows = {}

    def insert(self, key, value):
        self._rows[key] = value

    def get(self, key):
        return self._rows.get(key)

    def delete(self, key):
        self._rows.pop(key, None)

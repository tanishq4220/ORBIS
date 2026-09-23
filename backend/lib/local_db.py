"""In-memory operators/connections store for local demos when MongoDB is unavailable."""

from __future__ import annotations

import copy
from typing import Any, Optional


class _LocalCollection:
    def __init__(self, key_field: str = "_id") -> None:
        self._key_field = key_field
        self._docs: dict[str, dict[str, Any]] = {}

    def _key_from_query(self, query: dict[str, Any]) -> Optional[str]:
        if self._key_field in query and query[self._key_field] is not None:
            return str(query[self._key_field])
        if "email" in query and query["email"] is not None:
            return str(query["email"]).lower()
        return None

    async def find_one(self, query: dict[str, Any]) -> Optional[dict[str, Any]]:
        if "token_hash" in query:
            for doc in self._docs.values():
                if doc.get("token_hash") == query["token_hash"]:
                    return copy.deepcopy(doc)
        if "email" in query and query["email"] is not None:
            doc = self._docs.get(str(query["email"]).lower())
            return copy.deepcopy(doc) if doc else None
        key = self._key_from_query(query)
        if key is not None and key in self._docs:
            return copy.deepcopy(self._docs[key])
        if "id" in query:
            for doc in self._docs.values():
                if str(doc.get("id")) == str(query["id"]):
                    return copy.deepcopy(doc)
        return None

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> None:
        set_on_insert = update.get("$setOnInsert", {})
        set_fields = update.get("$set", {})

        if "email" in query:
            key = str(query["email"]).lower()
        else:
            key = self._key_from_query(query)

        if key is None:
            return

        existing = self._docs.get(key)
        if existing is None:
            if not upsert:
                return
            doc = {**set_on_insert, **set_fields}
            if "email" in query:
                doc.setdefault("email", key)
            if self._key_field in query:
                doc.setdefault(self._key_field, query[self._key_field])
            self._docs[key] = doc
            return
        existing.update(set_fields)

    async def insert_one(self, doc: dict[str, Any]) -> None:
        if "email" in doc:
            key = str(doc["email"]).lower()
        elif self._key_field in doc:
            key = str(doc[self._key_field])
        else:
            key = str(doc.get("id", len(self._docs)))
        if key in self._docs:
            from pymongo.errors import DuplicateKeyError

            raise DuplicateKeyError("document already exists")
        self._docs[key] = dict(doc)


class LocalDB:
    def __init__(self) -> None:
        self.operators = _LocalCollection(key_field="email")
        self.connections = _LocalCollection(key_field="_id")
        self.password_reset_tokens = _LocalCollection(key_field="email")

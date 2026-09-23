"""Shared Mongo handle — import `client`/`db` from here (server.py, routers, seed.py)."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, IndexModel

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# Local demo fallback when MongoDB is not running (set ORBIS_OFFLINE_AUTH=1).
_USE_LOCAL = os.environ.get("ORBIS_OFFLINE_AUTH", "").strip().lower() in {
    "1",
    "true",
    "yes",
}

client = None
if _USE_LOCAL:
    from lib.local_db import LocalDB

    db = LocalDB()
    logger.warning("ORBIS_OFFLINE_AUTH enabled — using in-memory operators store")
else:
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ["MONGO_URL"]
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ["DB_NAME"]]

from lib.reset_tokens import TOKEN_EXPIRY_SECONDS

# One entry per collection: every field a route filters, sorts, or dedupes on. Applied by ensure_indexes() at startup.
INDEXES: dict[str, list[IndexModel]] = {
    "operators": [IndexModel([("email", ASCENDING)], name="email", unique=True), IndexModel([("id", ASCENDING)], name="id", unique=True)],
    "status_checks": [IndexModel([("timestamp", DESCENDING)], name="timestamp_desc")],
    "password_reset_tokens": [
        IndexModel([("email", ASCENDING)], name="email"),
        IndexModel([("token_hash", ASCENDING)], name="token_hash", unique=True),
        IndexModel([("created_at", ASCENDING)], name="created_at_ttl", expireAfterSeconds=TOKEN_EXPIRY_SECONDS),
    ],
    # Conjunction screening history (summaries for list endpoint)
    "screening_history": [
        IndexModel([("timestamp_utc", DESCENDING)], name="timestamp_desc"),
        IndexModel([("target_id", ASCENDING)], name="target_id"),
    ],
    # Conjunction screening history (full results for replay endpoint)
    "screening_history_full": [
        IndexModel([("timestamp_utc", DESCENDING)], name="timestamp_desc"),
    ],
}


async def ensure_indexes() -> None:
    if _USE_LOCAL or client is None:
        return
    for collection, models in INDEXES.items():
        for model in models:  # one at a time so a bad spec skips only itself
            try:
                await db[collection].create_indexes([model])
            except Exception as exc:  # never block boot on an index; the log line names what to fix
                logger.error("ensure_indexes(%s.%s): %s", collection, model.document["name"], exc)

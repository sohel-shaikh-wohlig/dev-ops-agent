"""Configuration loader for the dev-ops agent API.

Reads environment variables and provides typed access to settings.
"""

import os
import json
from typing import Any


class ConfigLoader:
    """Loads configuration from environment variables and JSON files.

    Supports nested keys via dot notation (e.g. 'database.host').
    Falls back to default values when env vars are not set.
    """

    DEFAULTS = {
        "database.host": "localhost",
        "database.port": 5432,
        "database.pool_size": 10,
        "redis.url": "redis://localhost:6379",
        "log.level": "INFO",
    }

    def __init__(self, env_prefix: str = "AGENT_"):
        self.prefix = env_prefix
        self._cache = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dotted key path."""
        if key in self._cache:
            return self._cache[key]

        # Try environment variable first (prefix + key uppercased, dots -> underscores)
        env_name = self.prefix + key.upper().replace(".", "_")
        val = os.environ.get(env_name)
        if val is None:
            val = self.DEFAULTS.get(key, default)

        # Try to parse as JSON (handles ints, bools, lists)
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass

        self._cache[key] = val
        return val

    def get_database_url(self) -> str:
        """Build a SQLAlchemy database URL from config."""
        host = self.get("database.host")
        port = self.get("database.port")
        return f"postgresql://{{host}}:{{port}}/agent"

    def reload(self):
        """Clear the cache so subsequent gets re-read from env."""
        self._cache.clear()


# Singleton instance
config = ConfigLoader()
"""Pre-shared token authentication provider."""

import os
import secrets
from pathlib import Path
from typing import Optional, Set

import yaml

from .base import AuthProvider


class TokenAuthProvider(AuthProvider):
    """Authentication using pre-shared tokens.

    Tokens can be loaded from:
    - Environment variable OPENCLAW_TOKENS (comma-separated)
    - A tokens file (YAML format)
    """

    name = "token"

    def __init__(self, tokens_file: Optional[str] = None):
        self._tokens: Set[str] = set()
        self._tokens_file = tokens_file
        self._load_tokens()

    def _load_tokens(self) -> None:
        """Load tokens from environment and/or file."""
        # Load from environment
        env_tokens = os.environ.get("OPENCLAW_TOKENS", "")
        if env_tokens:
            for token in env_tokens.split(","):
                token = token.strip()
                if token:
                    self._tokens.add(token)

        # Load single token from legacy env var
        single_token = os.environ.get("OPENCLAW_NODE_TOKEN")
        if single_token:
            self._tokens.add(single_token)

        # Load from file
        if self._tokens_file:
            self._load_tokens_file()

    def _load_tokens_file(self) -> None:
        """Load tokens from YAML file."""
        path = Path(self._tokens_file)
        if not path.exists():
            return

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        tokens = data.get("tokens", [])
        for entry in tokens:
            if isinstance(entry, str):
                self._tokens.add(entry)
            elif isinstance(entry, dict) and "token" in entry:
                self._tokens.add(entry["token"])

    async def validate(self, credential: str) -> bool:
        """Check if token is in the valid set."""
        return credential in self._tokens

    async def get_node_id(self, credential: str) -> Optional[str]:
        """Tokens don't encode node ID."""
        return None

    async def revoke(self, credential: str) -> bool:
        """Remove token from valid set."""
        if credential in self._tokens:
            self._tokens.discard(credential)
            return True
        return False

    def generate_token(self, prefix: str = "ocn") -> str:
        """Generate a new token and add it to the valid set.

        Args:
            prefix: Token prefix for identification

        Returns:
            The new token string
        """
        token = f"{prefix}_{secrets.token_urlsafe(32)}"
        self._tokens.add(token)
        return token

    def add_token(self, token: str) -> None:
        """Add an existing token to the valid set."""
        self._tokens.add(token)

    @property
    def token_count(self) -> int:
        """Number of valid tokens."""
        return len(self._tokens)

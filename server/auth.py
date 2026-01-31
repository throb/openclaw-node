"""Authentication for node connections."""

import os
import secrets
from typing import Optional


class NodeAuth:
    """Handle node authentication."""
    
    def __init__(self):
        # Load valid tokens from environment or config
        self._valid_tokens: set = set()
        self._load_tokens()
    
    def _load_tokens(self):
        """Load valid tokens from environment."""
        # TODO: Load from secure config
        token = os.environ.get("OPENCLAW_NODE_TOKEN")
        if token:
            self._valid_tokens.add(token)
    
    def validate_token(self, token: str) -> bool:
        """Check if a token is valid."""
        return token in self._valid_tokens
    
    def generate_token(self) -> str:
        """Generate a new node token."""
        token = secrets.token_urlsafe(32)
        self._valid_tokens.add(token)
        return token
    
    def revoke_token(self, token: str):
        """Revoke a node token."""
        self._valid_tokens.discard(token)

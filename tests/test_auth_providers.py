"""Tests for authentication providers."""

import os
import pytest

from server.auth_providers.token import TokenAuthProvider


class TestTokenAuthProvider:
    """Tests for TokenAuthProvider."""

    def test_init_empty(self):
        """Provider initializes with no tokens."""
        # Clear env vars
        old_tokens = os.environ.pop("OPENCLAW_TOKENS", None)
        old_token = os.environ.pop("OPENCLAW_NODE_TOKEN", None)

        try:
            provider = TokenAuthProvider()
            assert provider.token_count == 0
        finally:
            if old_tokens:
                os.environ["OPENCLAW_TOKENS"] = old_tokens
            if old_token:
                os.environ["OPENCLAW_NODE_TOKEN"] = old_token

    def test_init_from_env(self):
        """Provider loads tokens from environment."""
        os.environ["OPENCLAW_NODE_TOKEN"] = "env-token-123"
        provider = TokenAuthProvider()
        assert provider.token_count >= 1

    @pytest.mark.asyncio
    async def test_validate_valid_token(self):
        """Valid token passes validation."""
        provider = TokenAuthProvider()
        token = provider.generate_token()
        assert await provider.validate(token) is True

    @pytest.mark.asyncio
    async def test_validate_invalid_token(self):
        """Invalid token fails validation."""
        provider = TokenAuthProvider()
        assert await provider.validate("invalid-token") is False

    @pytest.mark.asyncio
    async def test_revoke_token(self):
        """Revoking token removes it from valid set."""
        provider = TokenAuthProvider()
        token = provider.generate_token()
        assert await provider.validate(token) is True

        result = await provider.revoke(token)
        assert result is True
        assert await provider.validate(token) is False

    def test_generate_token_format(self):
        """Generated tokens have correct format."""
        provider = TokenAuthProvider()
        token = provider.generate_token(prefix="test")
        assert token.startswith("test_")
        assert len(token) > 10

    def test_add_token(self):
        """Can add existing token to valid set."""
        provider = TokenAuthProvider()
        provider.add_token("custom-token")
        assert provider.token_count >= 1

    @pytest.mark.asyncio
    async def test_get_node_id_returns_none(self):
        """Token provider doesn't encode node ID."""
        provider = TokenAuthProvider()
        token = provider.generate_token()
        assert await provider.get_node_id(token) is None

"""OAuth authentication provider stub for future implementation."""

from typing import Optional

from .base import AuthProvider


class OAuthProvider(AuthProvider):
    """OAuth 2.0 authentication provider.

    This is a stub for future implementation. When completed, it will support:
    - Authorization code flow for web clients
    - Client credentials flow for service accounts
    - JWT token validation
    """

    name = "oauth"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        issuer_url: Optional[str] = None,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._issuer_url = issuer_url
        # TODO: Initialize OAuth client, JWKS cache, etc.

    async def validate(self, credential: str) -> bool:
        """Validate JWT token.

        TODO: Implement JWT validation with:
        - Signature verification using JWKS
        - Expiration check
        - Audience/issuer validation
        """
        raise NotImplementedError("OAuth provider not yet implemented")

    async def get_node_id(self, credential: str) -> Optional[str]:
        """Extract node_id from JWT claims.

        TODO: Parse JWT and extract custom claim for node ID
        """
        raise NotImplementedError("OAuth provider not yet implemented")

    async def revoke(self, credential: str) -> bool:
        """Revoke is handled by the OAuth provider, not us."""
        return False

"""Base authentication provider interface."""

from abc import ABC, abstractmethod
from typing import Optional


class AuthProvider(ABC):
    """Abstract base class for authentication providers.

    Implement this to create custom auth methods (tokens, OAuth, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'token', 'oauth')."""
        ...

    @abstractmethod
    async def validate(self, credential: str) -> bool:
        """Validate a credential (token, JWT, etc.).

        Args:
            credential: The credential string to validate

        Returns:
            True if valid, False otherwise
        """
        ...

    @abstractmethod
    async def get_node_id(self, credential: str) -> Optional[str]:
        """Extract node ID from credential if applicable.

        Some auth methods may encode the node ID in the token.
        Return None if not applicable or invalid.
        """
        ...

    async def revoke(self, credential: str) -> bool:
        """Revoke a credential. Optional for stateless providers.

        Returns:
            True if revoked, False if not applicable or failed
        """
        return False

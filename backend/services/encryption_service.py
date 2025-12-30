"""
Encryption Service for API Keys
Uses Fernet (symmetric encryption) for secure storage of API keys in database.
"""

import os
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Handles encryption/decryption of sensitive data like API keys.
    Uses Fernet symmetric encryption with a key derived from environment variables.
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._init_encryption()

    def _init_encryption(self):
        """Initialize Fernet with key derived from environment secret."""
        # Get encryption key from environment (required for production)
        secret = os.getenv(
            "SCORATIS_ENCRYPTION_KEY",
            "scoratis-default-dev-key-change-in-production-32chars"
        )
        salt = os.getenv(
            "SCORATIS_ENCRYPTION_SALT",
            "scoratis-salt-value"
        ).encode()

        # Derive a secure key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        self._fernet = Fernet(key)

        logger.info("Encryption service initialized")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string and return base64-encoded ciphertext.

        Args:
            plaintext: The text to encrypt (e.g., API key)

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a base64-encoded ciphertext and return plaintext.

        Args:
            ciphertext: The encrypted text from database

        Returns:
            Original plaintext (e.g., API key)
        """
        if not ciphertext:
            return ""
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid token (key may have changed)")
            raise ValueError("Failed to decrypt API key - encryption key may have changed")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt API key")

    def is_encrypted(self, text: str) -> bool:
        """Check if a string appears to be Fernet-encrypted."""
        if not text:
            return False
        try:
            # Fernet tokens are base64 with specific structure
            decoded = base64.urlsafe_b64decode(text.encode())
            return len(decoded) > 0 and decoded[0] == 0x80
        except Exception:
            return False

    def mask_key(self, key: str, visible_chars: int = 8) -> str:
        """
        Mask an API key for display (e.g., "sk-abc...xyz").

        Args:
            key: The API key to mask
            visible_chars: Number of characters to show at start and end

        Returns:
            Masked key like "sk-abcd...wxyz"
        """
        if not key:
            return ""
        if len(key) <= visible_chars * 2:
            return "*" * len(key)
        return f"{key[:visible_chars]}...{key[-visible_chars:]}"


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service

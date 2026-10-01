"""Encryption utilities for sensitive data."""

import base64
import hashlib
import os
from typing import Any

from cryptography.fernet import Fernet
from django.conf import settings


class EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.

    Uses Fernet symmetric encryption with AES-128-CBC.
    """

    def __init__(self, key: str | None = None):
        """
        Initialize encryption manager.

        Args:
            key: Base64-encoded encryption key. If None, uses settings.CRYPTOGRAPHY_KEY
        """
        if key is None:
            key = getattr(settings, "CRYPTOGRAPHY_KEY", None)

        if key is None:
            # Generate a new key for development
            self.fernet = Fernet(Fernet.generate_key())
        else:
            # Ensure key is properly encoded
            if isinstance(key, str):
                key = key.encode()
            self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext.

        Args:
            plaintext: Text to encrypt

        Returns:
            Base64-encoded encrypted text
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()

        encrypted = self.fernet.encrypt(plaintext)
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext.

        Args:
            ciphertext: Base64-encoded encrypted text

        Returns:
            Decrypted plaintext
        """
        ciphertext_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self.fernet.decrypt(ciphertext_bytes)
        return decrypted.decode()

    @staticmethod
    def hash_for_lookup(value: str) -> str:
        """
        Create a hash for lookup purposes (e.g., CPF search).

        This allows searching for encrypted data without decrypting.

        Args:
            value: Value to hash

        Returns:
            SHA-256 hash of the value
        """
        return hashlib.sha256(value.encode()).hexdigest()


def encrypt_cpf(cpf: str) -> tuple[str, str]:
    """
    Encrypt a CPF for storage.

    Returns:
        Tuple of (encrypted_cpf, lookup_hash)
    """
    manager = EncryptionManager()
    encrypted = manager.encrypt(cpf)
    lookup_hash = manager.hash_for_lookup(cpf)
    return encrypted, lookup_hash


def decrypt_cpf(encrypted_cpf: str) -> str:
    """
    Decrypt a CPF.

    Args:
        encrypted_cpf: Encrypted CPF string

    Returns:
        Decrypted CPF
    """
    manager = EncryptionManager()
    return manager.decrypt(encrypted_cpf)


class DataMasker:
    """Utility for masking sensitive data for logs and displays."""

    @staticmethod
    def mask_cpf(cpf: str) -> str:
        """Mask CPF showing only last 4 digits."""
        if len(cpf) < 4:
            return "*" * len(cpf)
        return "***.***.***-" + cpf[-4:]

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email showing first 2 chars and domain."""
        if "@" not in email:
            return "**"
        local, domain = email.split("@", 1)
        masked_local = local[:2] + "***" if len(local) > 2 else "***"
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_card_number(number: str) -> str:
        """Mask card number showing only last 4 digits."""
        if len(number) < 4:
            return "*" * len(number)
        return "**** **** **** " + number[-4:]

    @staticmethod
    def mask_amount(amount: str | float) -> str:
        """Mask amount for logs (show only first digit)."""
        amount_str = str(amount)
        if len(amount_str) <= 1:
            return "*"
        return amount_str[0] + "***"
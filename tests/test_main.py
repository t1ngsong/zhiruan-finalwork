import pytest
from pathlib import Path
from unittest.mock import patch
from agent.main import _encrypt, _decrypt, _get_secrets_file


def test_encrypt_decrypt_roundtrip():
    plaintext = "sk-test-api-key-12345"
    password = "strong-password"
    encrypted = _encrypt(plaintext, password)
    decrypted = _decrypt(encrypted, password)
    assert decrypted == plaintext


def test_decrypt_wrong_password():
    plaintext = "sk-test-key"
    encrypted = _encrypt(plaintext, "correct-password")
    with pytest.raises(Exception):
        _decrypt(encrypted, "wrong-password")


def test_encrypt_produces_different_ciphertexts():
    """相同明文加密两次产生不同密文（不同 salt + nonce）"""
    c1 = _encrypt("test", "pw")
    c2 = _encrypt("test", "pw")
    assert c1 != c2

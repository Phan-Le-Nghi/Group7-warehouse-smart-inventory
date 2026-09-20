from warehouse_api.auth_service import (
    hash_password,
    hash_session_token,
    normalize_login_identifier,
    verify_password,
)


def test_password_hash_uses_argon2id_without_plaintext() -> None:
    password = "test-only-password"

    encoded_hash = hash_password(password)

    assert encoded_hash.startswith("$argon2id$")
    assert password not in encoded_hash
    assert verify_password(password, encoded_hash)
    assert not verify_password("wrong-password", encoded_hash)


def test_unknown_password_hash_is_rejected() -> None:
    assert not verify_password("password", "not-a-supported-hash")


def test_login_identifier_is_trimmed_and_lowercased() -> None:
    assert normalize_login_identifier("  Demo.Manager  ") == "demo.manager"


def test_session_token_hash_is_a_sha256_digest() -> None:
    digest = hash_session_token("test-token")

    assert isinstance(digest, bytes)
    assert len(digest) == 32
    assert b"test-token" not in digest

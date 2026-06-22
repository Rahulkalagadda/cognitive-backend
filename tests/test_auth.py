import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    get_assessment_token_hash,
)


def test_password_hashing():
    """Verify password hashing and validation matches constraints."""
    plain = "secure_clinician_pass_123"
    hashed = get_password_hash(plain)
    
    # Assert bcrypt prefix format matches database constraint: $2b$12$...
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert len(hashed) == 60
    
    # Assert successful verification
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong_pass", hashed) is False


def test_jwt_lifecycle():
    """Verify JWT access tokens encode and decode correctly."""
    subject = "cccccccc-0000-0000-0000-000000000001"
    token = create_access_token(subject=subject)
    
    decoded = decode_access_token(token)
    assert decoded == subject


def test_token_hash():
    """Verify URL tokens generate exactly 64-character SHA-256 hex hashes."""
    raw_token = "some_random_urlsafe_token_string_here"
    hashed = get_assessment_token_hash(raw_token)
    
    assert len(hashed) == 64
    # Check hex format
    import re
    assert re.match(r"^[a-f0-9]{64}$", hashed) is not None

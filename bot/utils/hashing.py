import hashlib


def hash_user(user_id: int, guild_id: int, salt: str = "tsd-default-salt") -> str:
    """SHA256 hash of user_id + guild_id + salt, truncated to 32 chars."""
    payload = f"{user_id}{guild_id}{salt}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]

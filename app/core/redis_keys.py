"""Redis 키 패턴 (database.md Redis 섹션 참조). 문자열 중복을 피하기 위해 한 곳에 모은다."""


def email_code_key(email: str) -> str:
    return f"email_verify:{email}"


def email_cooldown_key(email: str) -> str:
    return f"email_verify:cooldown:{email}"


def email_verified_key(email: str) -> str:
    return f"email_verified:{email}"


def refresh_token_key(user_id: int) -> str:
    return f"refresh_token:{user_id}"


def access_blacklist_key(jti: str) -> str:
    return f"access_blacklist:{jti}"


def chat_history_key(user_id: int) -> str:
    return f"chat:history:{user_id}"

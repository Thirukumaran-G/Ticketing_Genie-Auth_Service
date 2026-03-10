from passlib.context import CryptContext
import secrets
import string


_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password."""
    return str(_pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the hashed password."""
    return bool(_pwd_context.verify(plain, hashed))

def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        # Enforce complexity
        if (
            any(c.isupper() for c in password)
            and any(c.islower() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*" for c in password)
        ):
            return password
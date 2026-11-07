from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import jwt
import psycopg
from passlib.context import CryptContext

from backend.app.config import ALGORITHM, DATABASE_URL, SECRET_KEY, TOKEN_EXPIRE_MINUTES
from backend.app.data.customers import customers as CUSTOMER_RECORDS
from backend.app.data.users import users as USER_RECORDS


_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _connect_user_database() -> psycopg.Connection:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL must be configured to use authentication.")
    return psycopg.connect(DATABASE_URL)


def _initialize_user_database() -> None:
    with _connect_user_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS registered_users (
                username TEXT NOT NULL PRIMARY KEY,
                username_key TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                email_key TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                customer_id TEXT,
                hashed_password TEXT NOT NULL
            )
            """
        )
_initialize_user_database()


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer.")
    return _password_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against its bcrypt hash."""
    if len(plain.encode("utf-8")) > 72:
        return False
    return _password_context.verify(plain, hashed)


def _load_users() -> dict[str, dict[str, Any]]:
    users_by_username: dict[str, dict[str, Any]] = {}
    for record in USER_RECORDS:
        username = record.get("username") or record.get("name")
        password = record.get("password")
        if not isinstance(username, str) or not username:
            continue
        user = {key: value for key, value in record.items() if key != "password"}
        user["username"] = username
        user["customer_id"] = record.get("customer_id")
        user["hashed_password"] = (
            hash_password(password) if isinstance(password, str) and password else None
        )
        users_by_username[username] = user

    with _connect_user_database() as connection:
        records = connection.execute(
            """
            SELECT username, email, role, customer_id, hashed_password
            FROM registered_users
            """
        ).fetchall()

    for username, email, role, customer_id, hashed_password in records:
        users_by_username[username] = {
            "username": username,
            "email": email,
            "role": role,
            "customer_id": customer_id,
            "hashed_password": hashed_password,
        }
        if role == "customer" and not any(
            customer.get("customer_id") == customer_id
            for customer in CUSTOMER_RECORDS
        ):
            CUSTOMER_RECORDS.append(
                {"customer_id": customer_id, "name": username}
            )
    return users_by_username


USERS = _load_users()


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """Return a user with valid credentials, excluding its stored hash."""
    user = USERS.get(username)
    hashed_password = user.get("hashed_password") if user else None
    if not isinstance(hashed_password, str) or not verify_password(password, hashed_password):
        return None
    return {key: value for key, value in user.items() if key != "hashed_password"}


def register_user(
    username: str,
    password: str,
    email: str,
    role: str,
) -> dict[str, str]:
    normalized_username = username.strip()
    normalized_email = email.strip().casefold()
    if not normalized_username:
        raise ValueError("Username is required.")
    if any(
        existing.casefold() == normalized_username.casefold()
        for existing in USERS
    ):
        raise ValueError("That username is already registered.")
    if any(
        isinstance(user.get("email"), str)
        and user["email"].casefold() == normalized_email
        for user in USERS.values()
    ):
        raise ValueError("That email address is already registered.")

    user: dict[str, Any] = {
        "username": normalized_username,
        "email": normalized_email,
        "role": role,
        "customer_id": normalized_username if role == "customer" else None,
        "hashed_password": hash_password(password),
    }

    try:
        with _connect_user_database() as connection:
            connection.execute(
                """
                INSERT INTO registered_users (
                    username, username_key, email, email_key,
                    role, customer_id, hashed_password
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    normalized_username,
                    normalized_username.casefold(),
                    normalized_email,
                    normalized_email,
                    role,
                    user["customer_id"],
                    user["hashed_password"],
                ),
            )
    except psycopg.IntegrityError as exc:
        raise ValueError(
            "That username or email address is already registered."
        ) from exc

    USERS[normalized_username] = user

    if role == "customer":
        CUSTOMER_RECORDS.append(
            {"customer_id": normalized_username, "name": normalized_username}
        )

    return {"username": normalized_username, "email": normalized_email, "role": role}


def create_access_token(user: Mapping[str, Any]) -> str:
    """Sign a JWT containing the user's identity and configured expiry."""
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be configured before creating access tokens")

    username = user.get("username") or user.get("name")
    if not isinstance(username, str) or not username:
        raise ValueError("User must have a username")

    now = datetime.now(timezone.utc)
    payload = {
        "username": username,
        "role": user.get("role"),
        "customer_id": user.get("customer_id"),
        "exp": now + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode a signed JWT; PyJWT raises for invalid and expired tokens."""
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be configured before decoding access tokens")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return dict(payload)

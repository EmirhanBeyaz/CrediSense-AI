from __future__ import annotations

"""Kullanici ve oturum deposu.

Bu modul urun prototipinde gercek bir veritabani davranisi saglamak icin SQLite kullanir.
Sifreler duz metin saklanmaz; standart kutuphane ile PBKDF2-HMAC hash uretilir.
"""

import hashlib
import hmac
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


DEFAULT_USER_STORE = Path("veri") / "credisense_kullanicilar.db"
PASSWORD_ITERATIONS = 120_000
TOKEN_LIFETIME_HOURS = 8
EMAIL_TOKEN_LIFETIME_MINUTES = 15


def initialize_user_database(
    store_path: str | Path = DEFAULT_USER_STORE,
    seed_demo_users: bool = True,
) -> None:
    """SQLite veritabanini hazirlar.

    Tablo yapisi burada olusturulur. Demo kullanicilar istenirse SQLite icine
    gercek kayit olarak eklenir. Login islemi kullanici uretmez, sadece tablodan
    okuma ve sifre kontrolu yapar.
    """

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)

    if seed_demo_users:
        create_default_users(store_path=store_path)


def create_default_users(store_path: str | Path = DEFAULT_USER_STORE) -> None:
    """Demo urun akisinda kullanilacak varsayilan kullanicilari olusturur."""

    default_users = [
        {
            "user_id": "USR-CUSTOMER-DENIZ",
            "username": "user",
            "email": "user@gmail.com",
            "password": "123456",
            "role": "customer",
            "full_name": "Deniz Kaya",
            "title": "Premium müşteri",
            "profile": {
                "test_id": "11111111110",
                "birth_date": "12.04.1992",
                "employer": "Nova Veri Teknolojileri A.Ş.",
                "declared_income": "42350",
                "requested_credit": "300000",
                "maturity_months": "36",
                "existing_debt": "153000",
                "current_debt": 163420,
                "active_loan_id": "LOAN-DENIZ-001",
                "active_application_id": "APP-DENIZ-2026-001",
            },
        },
        {
            "user_id": "USR-EXPERT-AHMET",
            "username": "expert",
            "email": "expert@gmail.com",
            "password": "123456",
            "role": "expert",
            "full_name": "Ahmet Uzman",
            "title": "Kredi risk uzmanı",
            "profile": {
                "department": "Bireysel kredi risk",
                "branch": "Dijital inceleme",
            },
        },
    ]

    for user in default_users:
        existing_user = get_user_by_identifier(user["username"], store_path=store_path)
        if existing_user:
            if not existing_user.get("email_verified", False):
                _set_email_verified(existing_user["user_id"], store_path=store_path)
        else:
            create_user(
                user_id=user["user_id"],
                username=user["username"],
                email=user["email"],
                password=user["password"],
                role=user["role"],
                full_name=user["full_name"],
                title=user["title"],
                profile=user["profile"],
                email_verified=True,
                store_path=store_path,
            )


def create_user(
    user_id: str,
    username: str,
    email: str,
    password: str,
    role: str,
    full_name: str,
    title: str,
    profile: dict | None = None,
    email_verified: bool = False,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict:
    """Yeni kullanici olusturur ve genel kullanici bilgisini dondurur."""

    if role not in {"customer", "expert"}:
        raise ValueError("Kullanici rolu customer veya expert olmali.")

    salt = secrets.token_hex(16)
    password_hash = _hash_password(password, salt)
    profile = profile or {}

    path = _database_path(store_path)
    try:
        with sqlite3.connect(path) as connection:
            _create_tables_if_needed(connection)
            connection.execute(
                """
                INSERT INTO users (
                    user_id, username, email, role, full_name, title,
                    password_hash, salt, profile_json, email_verified, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username.lower().strip(),
                    email.lower().strip(),
                    role,
                    full_name,
                    title,
                    password_hash,
                    salt,
                    json.dumps(profile, ensure_ascii=False),
                    1 if email_verified else 0,
                    _now_iso(),
                ),
            )
    except sqlite3.IntegrityError as error:
        raise ValueError("Bu kullanici adi veya e-posta zaten kayitli.") from error

    return public_user_from_record(get_user_by_id(user_id, store_path=store_path) or {})


def register_user(
    username: str,
    email: str,
    password: str,
    role: str,
    full_name: str,
    title: str = "",
    profile: dict | None = None,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict:
    """Formdan gelen bilgilerle yeni kullanici kaydi olusturur."""

    cleaned_username = username.lower().strip()
    cleaned_email = email.lower().strip()
    if not cleaned_username:
        raise ValueError("Kullanici adi bos olamaz.")
    if "@" not in cleaned_email:
        raise ValueError("Gecerli bir e-posta adresi girilmeli.")
    if len(password) < 6:
        raise ValueError("Sifre en az 6 karakter olmali.")

    prefix = "CUST" if role == "customer" else "EXPERT"
    user_id = f"USR-{prefix}-{secrets.token_hex(6).upper()}"
    return create_user(
        user_id=user_id,
        username=cleaned_username,
        email=cleaned_email,
        password=password,
        role=role,
        full_name=full_name,
        title=title or ("Musteri" if role == "customer" else "Banka uzmani"),
        profile=profile,
        email_verified=False,
        store_path=store_path,
    )


def authenticate_user(
    identifier: str,
    password: str,
    role: str,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict | None:
    """Kullanici adi/e-posta, sifre ve rol eslesirse kullanici bilgisini dondurur."""

    initialize_user_database(store_path=store_path, seed_demo_users=False)
    user = get_user_by_identifier(identifier, store_path=store_path)
    if not user:
        return None

    if user.get("role") != role:
        return None

    if not user.get("email_verified", False):
        return None

    expected_hash = _hash_password(password, user.get("salt", ""))
    if not hmac.compare_digest(expected_hash, user.get("password_hash", "")):
        return None

    return public_user_from_record(user)


def create_session(
    user_id: str,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict:
    """Kullanici icin gecici bearer token olusturur."""

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_LIFETIME_HOURS)

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, expires_at.isoformat(), _now_iso()),
        )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }


def create_email_verification_token(
    user_id: str,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict:
    """Kullanici e-postasi icin tek kullanimlik dogrulama tokeni olusturur."""

    token = secrets.token_urlsafe(24)
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=EMAIL_TOKEN_LIFETIME_MINUTES)

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        connection.execute(
            """
            INSERT INTO email_verification_tokens (
                token_hash, user_id, expires_at, used_at, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (token_hash, user_id, expires_at.isoformat(), "", _now_iso()),
        )

    return {
        "token": token,
        "expires_at": expires_at.isoformat(),
    }


def verify_email_token(
    identifier: str,
    token: str,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict | None:
    """E-posta dogrulama tokenini kontrol eder ve kullaniciyi aktif eder."""

    user = get_user_by_identifier(identifier, store_path=store_path)
    if not user:
        return None

    token_hash = _hash_token(token.strip())
    now = _now_iso()
    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        row = connection.execute(
            """
            SELECT token_hash
            FROM email_verification_tokens
            WHERE token_hash = ?
              AND user_id = ?
              AND used_at = ''
              AND expires_at > ?
            """,
            (token_hash, user["user_id"], now),
        ).fetchone()

        if not row:
            return None

        connection.execute(
            "UPDATE email_verification_tokens SET used_at = ? WHERE token_hash = ?",
            (now, token_hash),
        )
        connection.execute(
            "UPDATE users SET email_verified = 1 WHERE user_id = ?",
            (user["user_id"],),
        )

    return public_user_from_record(get_user_by_id(user["user_id"], store_path=store_path) or {})


def get_user_by_token(token: str, store_path: str | Path = DEFAULT_USER_STORE) -> dict | None:
    """Bearer token ile kullanici kaydini dondurur."""

    if not token.strip():
        return None

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        row = connection.execute(
            """
            SELECT
                users.user_id, users.username, users.email, users.role,
                users.full_name, users.title, users.password_hash, users.salt,
                users.profile_json, users.email_verified, users.created_at
            FROM sessions
            JOIN users ON users.user_id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, _now_iso()),
        ).fetchone()

    return _row_to_user(row) if row else None


def get_user_by_identifier(
    identifier: str,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict | None:
    """Kullanici adi veya e-posta ile kullanici kaydini bulur."""

    normalized = identifier.lower().strip()
    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        row = connection.execute(
            """
            SELECT
                user_id, username, email, role, full_name, title,
                password_hash, salt, profile_json, email_verified, created_at
            FROM users
            WHERE username = ? OR email = ?
            """,
            (normalized, normalized),
        ).fetchone()

    return _row_to_user(row) if row else None


def get_user_by_id(user_id: str, store_path: str | Path = DEFAULT_USER_STORE) -> dict | None:
    """User ID ile kullanici kaydini dondurur."""

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        row = connection.execute(
            """
            SELECT
                user_id, username, email, role, full_name, title,
                password_hash, salt, profile_json, email_verified, created_at
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return _row_to_user(row) if row else None


def public_user_from_record(user: dict) -> dict:
    """Sifre alanlarini cikartarak frontend'e gonderilecek kullanici nesnesini uretir."""

    return {
        "id": user.get("user_id", ""),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "role": user.get("role", ""),
        "full_name": user.get("full_name", ""),
        "title": user.get("title", ""),
        "email_verified": bool(user.get("email_verified", False)),
        "profile": user.get("profile", {}),
    }


def update_user_profile(
    user_id: str,
    profile_updates: dict,
    store_path: str | Path = DEFAULT_USER_STORE,
) -> dict:
    """Kullanici profilindeki urun verilerini SQLite uzerinde gunceller."""

    user = get_user_by_id(user_id, store_path=store_path)
    if not user:
        raise ValueError("Kullanici bulunamadi.")

    profile = dict(user.get("profile", {}))
    profile.update(profile_updates)

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        connection.execute(
            "UPDATE users SET profile_json = ? WHERE user_id = ?",
            (json.dumps(profile, ensure_ascii=False), user_id),
        )

    return public_user_from_record(get_user_by_id(user_id, store_path=store_path) or {})


def _set_email_verified(user_id: str, store_path: str | Path) -> None:
    """Demo veya dogrulanmis kullanicinin e-posta durumunu aktif yapar."""

    path = _database_path(store_path)
    with sqlite3.connect(path) as connection:
        _create_tables_if_needed(connection)
        connection.execute("UPDATE users SET email_verified = 1 WHERE user_id = ?", (user_id,))


def _database_path(store_path: str | Path) -> Path:
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _create_tables_if_needed(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL,
            title TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            profile_json TEXT NOT NULL,
            email_verified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )
    _ensure_column(
        connection,
        table_name="users",
        column_name="email_verified",
        column_definition="INTEGER NOT NULL DEFAULT 0",
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS email_verification_tokens (
            token_hash TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """
    )


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    """Eski SQLite dosyalarinda eksik kolon varsa ekler."""

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    existing_columns = {row[1] for row in rows}
    if column_name not in existing_columns:
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def _row_to_user(row: tuple | None) -> dict:
    if not row:
        return {}

    return {
        "user_id": row[0],
        "username": row[1],
        "email": row[2],
        "role": row[3],
        "full_name": row[4],
        "title": row[5],
        "password_hash": row[6],
        "salt": row[7],
        "profile": json.loads(row[8]),
        "email_verified": bool(row[9]),
        "created_at": row[10],
    }


def _hash_password(password: str, salt: str) -> str:
    password_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt_bytes,
        PASSWORD_ITERATIONS,
    )
    return password_hash.hex()


def _hash_token(token: str) -> str:
    """Dogrulama tokenini veritabanina ham haliyle yazmamak icin hashler."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

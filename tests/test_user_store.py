from backend.credisense.kullanici_deposu import (
    authenticate_user,
    change_user_password,
    create_password_reset_token,
    create_email_verification_token,
    create_default_users,
    create_session,
    delete_user_account,
    get_user_by_token,
    initialize_user_database,
    register_user,
    reset_password_with_token,
    update_user_profile,
    verify_email_token,
)


def test_default_user_login_and_token_lookup(tmp_path) -> None:
    store_path = tmp_path / "users.db"

    create_default_users(store_path=store_path)
    user = authenticate_user(
        identifier="deniz.kaya",
        password="123456",
        role="customer",
        store_path=store_path,
    )

    assert user is not None
    assert user["full_name"] == "Deniz Kaya"
    assert user["profile"]["current_debt"] == 163420

    session = create_session(user["id"], store_path=store_path)
    stored_user = get_user_by_token(session["access_token"], store_path=store_path)

    assert stored_user is not None
    assert stored_user["user_id"] == "USR-CUSTOMER-DENIZ"


def test_login_rejects_wrong_password_or_role(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    create_default_users(store_path=store_path)

    wrong_password = authenticate_user(
        identifier="deniz.kaya",
        password="wrong",
        role="customer",
        store_path=store_path,
    )
    wrong_role = authenticate_user(
        identifier="deniz.kaya",
        password="123456",
        role="expert",
        store_path=store_path,
    )

    assert wrong_password is None
    assert wrong_role is None


def test_register_user_and_update_profile_with_sqlite(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    initialize_user_database(store_path=store_path, seed_demo_users=False)

    user = register_user(
        username="ayse.yilmaz",
        email="ayse@example.test",
        password="abcdef",
        role="customer",
        full_name="Ayse Yilmaz",
        profile={"current_debt": 50000},
        store_path=store_path,
    )

    assert user["username"] == "ayse.yilmaz"
    assert user["profile"]["current_debt"] == 50000

    assert authenticate_user(
        identifier="ayse@example.test",
        password="abcdef",
        role="customer",
        store_path=store_path,
    ) is None

    token_info = create_email_verification_token(user["id"], store_path=store_path)
    verified_user = verify_email_token(
        identifier="ayse@example.test",
        token=token_info["token"],
        store_path=store_path,
    )
    assert verified_user is not None

    login_user = authenticate_user(
        identifier="ayse@example.test",
        password="abcdef",
        role="customer",
        store_path=store_path,
    )
    assert login_user is not None
    assert login_user["id"] == user["id"]

    updated_user = update_user_profile(
        user["id"],
        {"current_debt": 42000, "active_loan_id": "LOAN-AYSE-001"},
        store_path=store_path,
    )
    assert updated_user["profile"]["current_debt"] == 42000
    assert updated_user["profile"]["active_loan_id"] == "LOAN-AYSE-001"


def test_change_user_password_updates_hash_without_plain_text(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    create_default_users(store_path=store_path)

    updated_user = change_user_password(
        identifier="deniz.kaya",
        new_password="yeni12345",
        store_path=store_path,
    )

    assert updated_user["username"] == "deniz.kaya"
    assert "password_hash" not in updated_user

    old_login = authenticate_user(
        identifier="deniz.kaya",
        password="123456",
        role="customer",
        store_path=store_path,
    )
    new_login = authenticate_user(
        identifier="deniz.kaya",
        password="yeni12345",
        role="customer",
        store_path=store_path,
    )

    assert old_login is None
    assert new_login is not None
    assert new_login["username"] == "deniz.kaya"


def test_password_reset_token_updates_password_and_invalidates_sessions(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    create_default_users(store_path=store_path)

    token_info = create_password_reset_token(
        email="deniz.kaya@example.test",
        role="customer",
        store_path=store_path,
    )
    reset_user = reset_password_with_token(
        email="deniz.kaya@example.test",
        role="customer",
        token=token_info["token"],
        new_password="yenisifre123",
        store_path=store_path,
    )

    assert reset_user is not None
    assert reset_user["email"] == "deniz.kaya@example.test"
    assert "password_hash" not in reset_user

    assert authenticate_user("deniz.kaya", "123456", "customer", store_path=store_path) is None
    assert authenticate_user("deniz.kaya", "yenisifre123", "customer", store_path=store_path) is not None

    reused_token = reset_password_with_token(
        email="deniz.kaya@example.test",
        role="customer",
        token=token_info["token"],
        new_password="baska123",
        store_path=store_path,
    )
    assert reused_token is None


def test_password_reset_verifies_unverified_email(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    initialize_user_database(store_path=store_path, seed_demo_users=False)
    user = register_user(
        username="mail.sahibi",
        email="mail.sahibi@example.test",
        password="eskisifre",
        role="customer",
        full_name="Mail Sahibi",
        store_path=store_path,
    )
    assert user["email_verified"] is False

    token_info = create_password_reset_token(
        email="mail.sahibi@example.test",
        role="customer",
        store_path=store_path,
    )
    reset_user = reset_password_with_token(
        email="mail.sahibi@example.test",
        role="customer",
        token=token_info["token"],
        new_password="yenisifre123",
        store_path=store_path,
    )

    assert reset_user is not None
    assert reset_user["email_verified"] is True
    assert authenticate_user(
        identifier="mail.sahibi@example.test",
        password="yenisifre123",
        role="customer",
        store_path=store_path,
    ) is not None


def test_delete_user_account_removes_user_and_session(tmp_path) -> None:
    store_path = tmp_path / "users.db"
    create_default_users(store_path=store_path)
    user = authenticate_user("deniz.kaya", "123456", "customer", store_path=store_path)
    assert user is not None
    session = create_session(user["id"], store_path=store_path)

    deleted_user = delete_user_account(user["id"], store_path=store_path)

    assert deleted_user["username"] == "deniz.kaya"
    assert authenticate_user("deniz.kaya", "123456", "customer", store_path=store_path) is None
    assert get_user_by_token(session["access_token"], store_path=store_path) is None

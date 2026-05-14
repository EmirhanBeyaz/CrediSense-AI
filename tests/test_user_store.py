from backend.credisense.kullanici_deposu import (
    authenticate_user,
    create_email_verification_token,
    create_default_users,
    create_session,
    get_user_by_token,
    initialize_user_database,
    register_user,
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

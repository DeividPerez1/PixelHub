from datetime import date
from types import SimpleNamespace

import pytest

from services.category_service import (
    category_to_dict,
    process_category_actions,
)
from services.post_service import post_to_dict, process_post_actions
from services.profile_service import profile_to_dict, process_profile_actions
from services.role_service import process_role_actions, role_to_dict
from services.tag_service import process_tag_actions, tag_to_dict
from services.user_service import process_user_actions, user_to_dict


def test_entity_serializers_convert_dates_to_iso_strings():
    today = date(2026, 10, 14)
    role = SimpleNamespace(
        id=1, name="admin", description="Administrator", last_update=today
    )
    profile = SimpleNamespace(
        id=2,
        user_id=8,
        first_name="Ada",
        last_name="Lovelace",
        bio=None,
        avatar_url=None,
        phone_number=None,
        location=None,
        birth_date=today,
        last_update=today,
    )
    post = SimpleNamespace(
        id=3,
        title="Hello",
        img=None,
        category_id=4,
        user_id=8,
        content="A post",
        creation_date=today,
        viewCount=0,
        last_update=today,
    )

    assert role_to_dict(role)["last_update"] == "2026-10-14"
    assert profile_to_dict(profile)["birth_date"] == "2026-10-14"
    assert post_to_dict(post)["creation_date"] == "2026-10-14"
    assert category_to_dict(SimpleNamespace(id=4, name="tech", last_update=today)) == {
        "id": 4,
        "name": "tech",
        "last_update": "2026-10-14",
    }
    assert tag_to_dict(SimpleNamespace(id=5, name="python", last_update=today)) == {
        "id": 5,
        "name": "python",
        "last_update": "2026-10-14",
    }
    assert user_to_dict(
        SimpleNamespace(id=8, username="ada", email="ada@example.test", role_id=1)
    ) == {
        "id": 8,
        "username": "ada",
        "email": "ada@example.test",
        "role_id": 1,
    }


@pytest.mark.parametrize(
    ("serializer", "entity"),
    [
        (role_to_dict, "role"),
        (category_to_dict, "category"),
        (tag_to_dict, "tag"),
        (user_to_dict, "user"),
        (profile_to_dict, "profile"),
        (post_to_dict, "post"),
    ],
)
def test_entity_serializers_handle_none(serializer, entity):
    assert serializer(None) is None


def test_add_role_saves_commits_and_serializes(repository, session):
    repository.save.side_effect = lambda role: setattr(role, "id", 12)

    response = process_role_actions(
        "add_role", {"name": "editor", "description": "Writes posts"}, repository, session
    )

    assert response == {
        "status": "ok",
        "message": "Role created successfully.",
        "data": {"id": 12, "name": "editor", "description": "Writes posts", "last_update": None},
    }
    repository.save.assert_called_once()
    session.commit.assert_called_once()


def test_update_role_rejects_unknown_attribute_without_committing(repository, session):
    repository.get.return_value = SimpleNamespace(id=12, name="editor", description=None)

    response = process_role_actions(
        "update_role",
        {"id": "12", "attribute": "is_admin", "new_value": True},
        repository,
        session,
    )

    assert response["status"] == "error"
    assert response["message"] == "Invalid role attribute."
    repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_update_role_updates_allowed_attribute(repository, session):
    role = SimpleNamespace(
        id=12, name="editor", description="Old description", last_update=None
    )
    repository.get.return_value = role

    response = process_role_actions(
        "update_role",
        {"id": "12", "attribute": "description", "new_value": "New description"},
        repository,
        session,
    )

    assert response["data"]["description"] == "New description"
    repository.update.assert_called_once_with(role)
    session.commit.assert_called_once()


def test_delete_role_returns_not_found(repository, session):
    repository.get.return_value = None

    response = process_role_actions("delete_role", {"id": "404"}, repository, session)

    assert response == {"status": "error", "message": "Role not found.", "data": None}
    repository.delete.assert_not_called()
    session.commit.assert_not_called()


def test_role_list_serializes_every_record(repository, session):
    repository.get_all.return_value = [
        SimpleNamespace(id=1, name="admin", description=None, last_update=None)
    ]

    response = process_role_actions("get_all_roles", {}, repository, session)

    assert response["data"] == [
        {"id": 1, "name": "admin", "description": None, "last_update": None}
    ]
    session.commit.assert_not_called()


def test_add_user_converts_role_id_and_hides_password(repository, session):
    repository.save.side_effect = lambda user: setattr(user, "id", 7)

    response = process_user_actions(
        "add_user",
        {
            "username": "ada",
            "email": "ada@example.test",
            "password": "secret",
            "role_id": "3",
        },
        repository,
        session,
    )

    assert response["data"] == {
        "id": 7,
        "username": "ada",
        "email": "ada@example.test",
        "role_id": 3,
    }
    assert "password" not in response["data"]
    session.commit.assert_called_once()


@pytest.mark.parametrize(
    ("action", "lookup", "payload", "record"),
    [
        (
            "get_user_by_username",
            "get_by_username",
            {"username": "ada"},
            SimpleNamespace(id=7, username="ada", email="ada@example.test", role_id=3),
        ),
        (
            "get_user_by_email",
            "get_by_email",
            {"email": "ada@example.test"},
            SimpleNamespace(id=7, username="ada", email="ada@example.test", role_id=3),
        ),
    ],
)
def test_user_lookup_uses_repository_and_serializes(
    repository, session, action, lookup, payload, record
):
    getattr(repository, lookup).return_value = record

    response = process_user_actions(action, payload, repository, session)

    assert response["status"] == "ok"
    assert response["data"]["username"] == "ada"
    getattr(repository, lookup).assert_called_once_with(next(iter(payload.values())))


def test_update_user_converts_role_id(repository, session):
    repository.get.return_value = SimpleNamespace(
        id=7, username="ada", email="ada@example.test", role_id=1
    )

    response = process_user_actions(
        "update_user",
        {"id": "7", "attribute": "role_id", "new_value": "3"},
        repository,
        session,
    )

    assert response["data"]["role_id"] == 3
    repository.update.assert_called_once()
    session.commit.assert_called_once()


def test_user_update_rejects_passwordless_unknown_attribute(repository, session):
    repository.get.return_value = SimpleNamespace(
        id=7, username="ada", email="ada@example.test", role_id=1
    )

    response = process_user_actions(
        "update_user",
        {"id": "7", "attribute": "is_admin", "new_value": True},
        repository,
        session,
    )

    assert response["message"] == "Invalid user attribute."
    repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_add_profile_parses_iso_birth_date(repository, session):
    repository.save.side_effect = lambda profile: setattr(profile, "id", 9)

    response = process_profile_actions(
        "add_profile",
        {
            "user_id": "7",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "birth_date": "1815-12-10",
        },
        repository,
        session,
    )

    assert response["data"]["user_id"] == 7
    assert response["data"]["birth_date"] == "1815-12-10"
    session.commit.assert_called_once()


def test_update_profile_parses_birth_date(repository, session):
    profile = SimpleNamespace(
        id=9,
        user_id=7,
        first_name="Ada",
        last_name="Lovelace",
        bio=None,
        avatar_url=None,
        phone_number=None,
        location=None,
        birth_date=date(1815, 12, 10),
        last_update=None,
    )
    repository.get.return_value = profile

    response = process_profile_actions(
        "update_profile",
        {"id": "9", "attribute": "birth_date", "new_value": "1816-01-01"},
        repository,
        session,
    )

    assert profile.birth_date == date(1816, 1, 1)
    assert response["data"]["birth_date"] == "1816-01-01"
    session.commit.assert_called_once()


def test_profile_update_rejects_unknown_attribute(repository, session):
    repository.get.return_value = SimpleNamespace(id=9)

    response = process_profile_actions(
        "update_profile",
        {"id": "9", "attribute": "is_admin", "new_value": True},
        repository,
        session,
    )

    assert response["message"] == "Invalid profile attribute."
    repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_add_post_converts_foreign_keys_and_serializes(repository, session):
    repository.save.side_effect = lambda post: setattr(post, "id", 21)

    response = process_post_actions(
        "add_post",
        {
            "category_id": "4",
            "user_id": "7",
            "title": "Hello",
            "content": "First post",
        },
        repository,
        session,
    )

    assert response["data"]["category_id"] == 4
    assert response["data"]["user_id"] == 7
    assert response["data"]["title"] == "Hello"
    session.commit.assert_called_once()


@pytest.mark.parametrize(
    ("action", "payload", "lookup", "expected_argument"),
    [
        ("get_posts_by_category", {"category_id": "4"}, "get_by_category", 4),
        ("get_posts_by_user", {"user_id": "7"}, "get_by_user", 7),
    ],
)
def test_post_filters_convert_ids(repository, session, action, payload, lookup, expected_argument):
    getattr(repository, lookup).return_value = []

    response = process_post_actions(action, payload, repository, session)

    assert response["status"] == "ok"
    getattr(repository, lookup).assert_called_once_with(expected_argument)


def test_update_post_converts_category_id(repository, session):
    post = SimpleNamespace(
        id=21,
        title="Hello",
        img=None,
        category_id=4,
        user_id=7,
        content="First post",
        creation_date=None,
        viewCount=0,
        last_update=None,
    )
    repository.get.return_value = post

    response = process_post_actions(
        "update_post",
        {"id": "21", "attribute": "category_id", "new_value": "8"},
        repository,
        session,
    )

    assert post.category_id == 8
    assert response["data"]["category_id"] == 8
    repository.update.assert_called_once_with(post)
    session.commit.assert_called_once()


def test_get_last_posts_serializes_repository_results(repository, session):
    repository.get_last.return_value = [
        SimpleNamespace(
            id=21,
            title="Hello",
            img=None,
            category_id=4,
            user_id=7,
            content="First post",
            creation_date=None,
            viewCount=0,
            last_update=None,
        )
    ]

    response = process_post_actions("get_last_posts", {}, repository, session)

    assert response["status"] == "ok"
    assert response["data"][0]["id"] == 21
    repository.get_last.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    ("action", "processor", "name", "item_id"),
    [
        ("add_category", process_category_actions, "tech", 31),
        ("add_tag", process_tag_actions, "python", 32),
    ],
)
def test_add_named_entities_saves_and_commits(
    repository, session, action, processor, name, item_id
):
    repository.save.side_effect = lambda item: setattr(item, "id", item_id)

    response = processor(action, {"name": name}, repository, session)

    assert response["status"] == "ok"
    assert response["data"]["name"] == name
    assert response["data"]["id"] == item_id
    session.commit.assert_called_once()


def test_update_category_changes_name_and_commits(repository, session):
    category = SimpleNamespace(id=31, name="old", last_update=None)
    repository.get.return_value = category

    response = process_category_actions(
        "update_category",
        {"id": "31", "attribute": "name", "new_value": "new"},
        repository,
        session,
    )

    assert response["data"]["name"] == "new"
    repository.update.assert_called_once_with(category)
    session.commit.assert_called_once()


def test_update_tag_rejects_unknown_attribute(repository, session):
    repository.get.return_value = SimpleNamespace(id=32, name="python")

    response = process_tag_actions(
        "update_tag",
        {"id": "32", "attribute": "description", "new_value": "language"},
        repository,
        session,
    )

    assert response["message"] == "Invalid tag attribute."
    repository.update.assert_not_called()
    session.commit.assert_not_called()


def test_unknown_service_action_returns_error_without_committing(repository, session):
    response = process_tag_actions("not_a_tag_action", {}, repository, session)

    assert response == {
        "status": "error",
        "message": "Unknown tag action.",
        "data": None,
    }
    session.commit.assert_not_called()

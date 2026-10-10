from domain.models import User


def user_to_dict(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role_id": user.role_id,
    }


def process_user_actions(action, data, repository, session):
    if action == "add_user":
        user = User(
            username=data.get("username"),
            email=data.get("email"),
            password=data.get("password"),
            role_id=int(data.get("role_id")),
        )
        repository.save(user)
        session.commit()
        return {
            "status": "ok",
            "message": "User created successfully.",
            "data": user_to_dict(user),
        }

    elif action == "delete_user":
        user_id = int(data.get("id"))
        user = repository.get(user_id)
        if user is None:
            return {"status": "error", "message": "User not found.", "data": None}
        repository.delete(user_id)
        session.commit()
        return {"status": "ok", "message": "User deleted successfully.", "data": None}

    elif action == "update_user":
        user = repository.get(int(data.get("id")))
        if user is None:
            return {"status": "error", "message": "User not found.", "data": None}
        attribute = data.get("attribute")
        if attribute not in {"username", "email", "password", "role_id"}:
            return {"status": "error", "message": "Invalid user attribute.", "data": None}
        new_value = data.get("new_value")
        if attribute == "role_id":
            new_value = int(new_value)
        setattr(user, attribute, new_value)
        repository.update(user)
        session.commit()
        return {
            "status": "ok",
            "message": "User updated successfully.",
            "data": user_to_dict(user),
        }

    elif action == "get_all_users":
        users = repository.get_all()
        return {
            "status": "ok",
            "message": "Users retrieved successfully.",
            "data": [user_to_dict(user) for user in users],
        }

    elif action == "get_user":
        user = repository.get(int(data.get("id")))
        if user is None:
            return {"status": "error", "message": "User not found.", "data": None}
        return {
            "status": "ok",
            "message": "User retrieved successfully.",
            "data": user_to_dict(user),
        }

    elif action == "get_user_by_username":
        user = repository.get_by_username(data.get("username"))
        if user is None:
            return {"status": "error", "message": "User not found.", "data": None}
        return {
            "status": "ok",
            "message": "User retrieved successfully.",
            "data": user_to_dict(user),
        }

    elif action == "get_user_by_email":
        user = repository.get_by_email(data.get("email"))
        if user is None:
            return {"status": "error", "message": "User not found.", "data": None}
        return {
            "status": "ok",
            "message": "User retrieved successfully.",
            "data": user_to_dict(user),
        }

    return {"status": "error", "message": "Unknown user action.", "data": None}

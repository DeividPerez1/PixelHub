from domain.models import Role


def role_to_dict(role):
    if role is None:
        return None
    return {
        "id": role.id,
        "name": role.name,
        "description": role.description,
        "last_update": role.last_update.isoformat() if role.last_update else None,
    }


def process_role_actions(action, data, repository, session):
    if action == "add_role":
        role = Role(name=data.get("name"), description=data.get("description"))
        repository.save(role)
        session.commit()
        return {
            "status": "ok",
            "message": "Role created successfully.",
            "data": role_to_dict(role),
        }

    elif action == "delete_role":
        role_id = int(data.get("id"))
        role = repository.get(role_id)
        if role is None:
            return {"status": "error", "message": "Role not found.", "data": None}
        repository.delete(role_id)
        session.commit()
        return {"status": "ok", "message": "Role deleted successfully.", "data": None}

    elif action == "update_role":
        role = repository.get(int(data.get("id")))
        if role is None:
            return {"status": "error", "message": "Role not found.", "data": None}
        attribute = data.get("attribute")
        if attribute not in {"name", "description"}:
            return {"status": "error", "message": "Invalid role attribute.", "data": None}
        setattr(role, attribute, data.get("new_value"))
        repository.update(role)
        session.commit()
        return {
            "status": "ok",
            "message": "Role updated successfully.",
            "data": role_to_dict(role),
        }

    elif action == "get_all_roles":
        roles = repository.get_all()
        return {
            "status": "ok",
            "message": "Roles retrieved successfully.",
            "data": [role_to_dict(role) for role in roles],
        }

    elif action == "get_role":
        role = repository.get(int(data.get("id")))
        if role is None:
            return {"status": "error", "message": "Role not found.", "data": None}
        return {
            "status": "ok",
            "message": "Role retrieved successfully.",
            "data": role_to_dict(role),
        }

    return {"status": "error", "message": "Unknown role action.", "data": None}

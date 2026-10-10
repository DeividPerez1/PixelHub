from domain.models import Tag


def tag_to_dict(tag):
    if tag is None:
        return None
    return {
        "id": tag.id,
        "name": tag.name,
        "last_update": tag.last_update.isoformat() if tag.last_update else None,
    }


def process_tag_actions(action, data, repository, session):
    if action == "add_tag":
        tag = Tag(name=data.get("name"))
        repository.save(tag)
        session.commit()
        return {
            "status": "ok",
            "message": "Tag created successfully.",
            "data": tag_to_dict(tag),
        }

    elif action == "delete_tag":
        tag_id = int(data.get("id"))
        tag = repository.get(tag_id)
        if tag is None:
            return {"status": "error", "message": "Tag not found.", "data": None}
        repository.delete(tag_id)
        session.commit()
        return {"status": "ok", "message": "Tag deleted successfully.", "data": None}

    elif action == "update_tag":
        tag = repository.get(int(data.get("id")))
        if tag is None:
            return {"status": "error", "message": "Tag not found.", "data": None}
        if data.get("attribute") != "name":
            return {"status": "error", "message": "Invalid tag attribute.", "data": None}
        tag.name = data.get("new_value")
        repository.update(tag)
        session.commit()
        return {
            "status": "ok",
            "message": "Tag updated successfully.",
            "data": tag_to_dict(tag),
        }

    elif action == "get_all_tags":
        tags = repository.get_all()
        return {
            "status": "ok",
            "message": "Tags retrieved successfully.",
            "data": [tag_to_dict(tag) for tag in tags],
        }

    elif action == "get_tag":
        tag = repository.get(int(data.get("id")))
        if tag is None:
            return {"status": "error", "message": "Tag not found.", "data": None}
        return {
            "status": "ok",
            "message": "Tag retrieved successfully.",
            "data": tag_to_dict(tag),
        }

    return {"status": "error", "message": "Unknown tag action.", "data": None}

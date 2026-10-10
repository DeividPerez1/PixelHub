from domain.models import Category


def category_to_dict(category):
    if category is None:
        return None
    return {
        "id": category.id,
        "name": category.name,
        "last_update": category.last_update.isoformat() if category.last_update else None,
    }


def process_category_actions(action, data, repository, session):
    if action == "add_category":
        category = Category(name=data.get("name"))
        repository.save(category)
        session.commit()
        return {
            "status": "ok",
            "message": "Category created successfully.",
            "data": category_to_dict(category),
        }

    elif action == "delete_category":
        category_id = int(data.get("id"))
        category = repository.get(category_id)
        if category is None:
            return {"status": "error", "message": "Category not found.", "data": None}
        repository.delete(category_id)
        session.commit()
        return {"status": "ok", "message": "Category deleted successfully.", "data": None}

    elif action == "update_category":
        category = repository.get(int(data.get("id")))
        if category is None:
            return {"status": "error", "message": "Category not found.", "data": None}
        attribute = data.get("attribute")
        if attribute != "name":
            return {"status": "error", "message": "Invalid category attribute.", "data": None}
        category.name = data.get("new_value")
        repository.update(category)
        session.commit()
        return {
            "status": "ok",
            "message": "Category updated successfully.",
            "data": category_to_dict(category),
        }

    elif action == "get_all_categories":
        categories = repository.get_all()
        return {
            "status": "ok",
            "message": "Categories retrieved successfully.",
            "data": [category_to_dict(category) for category in categories],
        }

    elif action == "get_category":
        category = repository.get(int(data.get("id")))
        if category is None:
            return {"status": "error", "message": "Category not found.", "data": None}
        return {
            "status": "ok",
            "message": "Category retrieved successfully.",
            "data": category_to_dict(category),
        }

    return {"status": "error", "message": "Unknown category action.", "data": None}

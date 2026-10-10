from domain.models import Post


def post_to_dict(post):
    if post is None:
        return None
    return {
        "id": post.id,
        "title": post.title,
        "img": post.img,
        "category_id": post.category_id,
        "user_id": post.user_id,
        "content": post.content,
        "creation_date": post.creation_date.isoformat() if post.creation_date else None,
        "viewCount": post.viewCount,
        "last_update": post.last_update.isoformat() if post.last_update else None,
    }


def process_post_actions(action, data, repository, session):
    if action == "add_post":
        post = Post(
            category_id=int(data.get("category_id")),
            user_id=int(data.get("user_id")),
            title=data.get("title"),
            content=data.get("content"),
            img=data.get("img"),
        )
        repository.save(post)
        session.commit()
        return {
            "status": "ok",
            "message": "Post created successfully.",
            "data": post_to_dict(post),
        }

    elif action == "delete_post":
        post_id = int(data.get("id"))
        post = repository.get(post_id)
        if post is None:
            return {"status": "error", "message": "Post not found.", "data": None}
        repository.delete(post_id)
        session.commit()
        return {"status": "ok", "message": "Post deleted successfully.", "data": None}

    elif action == "update_post":
        post = repository.get(int(data.get("id")))
        if post is None:
            return {"status": "error", "message": "Post not found.", "data": None}
        attribute = data.get("attribute")
        allowed_attributes = {"category_id", "user_id", "title", "content", "img"}
        if attribute not in allowed_attributes:
            return {"status": "error", "message": "Invalid post attribute.", "data": None}
        new_value = data.get("new_value")
        if attribute in {"category_id", "user_id"}:
            new_value = int(new_value)
        setattr(post, attribute, new_value)
        repository.update(post)
        session.commit()
        return {
            "status": "ok",
            "message": "Post updated successfully.",
            "data": post_to_dict(post),
        }

    elif action == "get_all_posts":
        posts = repository.get_all()
        return {
            "status": "ok",
            "message": "Posts retrieved successfully.",
            "data": [post_to_dict(post) for post in posts],
        }

    elif action == "get_post":
        post = repository.get(int(data.get("id")))
        if post is None:
            return {"status": "error", "message": "Post not found.", "data": None}
        return {
            "status": "ok",
            "message": "Post retrieved successfully.",
            "data": post_to_dict(post),
        }

    elif action == "get_posts_by_category":
        posts = repository.get_by_category(int(data.get("category_id")))
        return {
            "status": "ok",
            "message": "Posts retrieved successfully.",
            "data": [post_to_dict(post) for post in posts],
        }

    elif action == "get_posts_by_user":
        posts = repository.get_by_user(int(data.get("user_id")))
        return {
            "status": "ok",
            "message": "Posts retrieved successfully.",
            "data": [post_to_dict(post) for post in posts],
        }

    elif action == "get_last_posts":
        posts = repository.get_last()
        return {
            "status": "ok",
            "message": "Latest posts retrieved successfully.",
            "data": [post_to_dict(post) for post in posts],
        }

    return {"status": "error", "message": "Unknown post action.", "data": None}

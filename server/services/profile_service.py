from datetime import date

from domain.models import Profile


def _parse_date(value):
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(value)


def profile_to_dict(profile):
    if profile is None:
        return None
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "bio": profile.bio,
        "avatar_url": profile.avatar_url,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        "last_update": profile.last_update.isoformat() if profile.last_update else None,
    }


def process_profile_actions(action, data, repository, session):
    if action == "add_profile":
        profile = Profile(
            user_id=int(data.get("user_id")),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            bio=data.get("bio"),
            avatar_url=data.get("avatar_url"),
            phone_number=data.get("phone_number"),
            location=data.get("location"),
            birth_date=_parse_date(data.get("birth_date")),
        )
        repository.save(profile)
        session.commit()
        return {
            "status": "ok",
            "message": "Profile created successfully.",
            "data": profile_to_dict(profile),
        }

    elif action == "delete_profile":
        profile_id = int(data.get("id"))
        profile = repository.get(profile_id)
        if profile is None:
            return {"status": "error", "message": "Profile not found.", "data": None}
        repository.delete(profile_id)
        session.commit()
        return {"status": "ok", "message": "Profile deleted successfully.", "data": None}

    elif action == "update_profile":
        profile = repository.get(int(data.get("id")))
        if profile is None:
            return {"status": "error", "message": "Profile not found.", "data": None}
        attribute = data.get("attribute")
        allowed_attributes = {
            "user_id",
            "first_name",
            "last_name",
            "bio",
            "avatar_url",
            "phone_number",
            "location",
            "birth_date",
        }
        if attribute not in allowed_attributes:
            return {"status": "error", "message": "Invalid profile attribute.", "data": None}
        new_value = data.get("new_value")
        if attribute == "birth_date":
            new_value = _parse_date(new_value)
        elif attribute == "user_id":
            new_value = int(new_value)
        setattr(profile, attribute, new_value)
        repository.update(profile)
        session.commit()
        return {
            "status": "ok",
            "message": "Profile updated successfully.",
            "data": profile_to_dict(profile),
        }

    elif action == "get_all_profiles":
        profiles = repository.get_all()
        return {
            "status": "ok",
            "message": "Profiles retrieved successfully.",
            "data": [profile_to_dict(profile) for profile in profiles],
        }

    elif action == "get_profile":
        profile = repository.get(int(data.get("id")))
        if profile is None:
            return {"status": "error", "message": "Profile not found.", "data": None}
        return {
            "status": "ok",
            "message": "Profile retrieved successfully.",
            "data": profile_to_dict(profile),
        }

    return {"status": "error", "message": "Unknown profile action.", "data": None}

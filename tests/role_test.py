
from domain import Role, RoleRepository, UserRepository, engine
from domain.db import Session
import pytest

session = Session(bind=engine)

def test_role_not_empty():
    role_rep = RoleRepository(session)
    roles = role_rep.get_all()
    assert roles is not None, "La tabla role no debería estar vacía"
    assert len(roles) > 0, "Debe existir al menos un rol"

def test_user_table_not_empty():
    user_rep = UserRepository(session)
    users = user_rep.get_all()
    assert users is not None, "La tabla user no debería estar vacía"
    assert len(users) > 0, "Debe existir al menos un usuario"

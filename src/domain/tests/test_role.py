import pytest
from src.domain.repository import RoleRepository,Role
def test_given_one_name_of_role_verify_if_its_not_empty():
    invalid_name = ""
    
    # When & Then: al intentar crear el Role, debería lanzar una excepción
    with pytest.raises(ValueError) as excinfo:
        Role(name=invalid_name)
    

    # assert "El nombre no puede estar vacío" in str(excinfo.value)
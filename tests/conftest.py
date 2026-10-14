import os
import sys
from pathlib import Path
from unittest.mock import Mock

PROJECT_DIR = Path(__file__).resolve().parent.parent
SERVER_DIR = PROJECT_DIR / "server"
CLIENT_DIR = PROJECT_DIR / "client"

os.environ["ENVIROMENT"] = "test"
os.environ["DB_URL_TEST"] = "sqlite://"

for directory in (SERVER_DIR, CLIENT_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


import pytest


@pytest.fixture
def repository():
    return Mock()


@pytest.fixture
def session():
    return Mock()

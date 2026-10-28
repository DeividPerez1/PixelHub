# PixelHub

PixelHub is a back-office application that performs CRUD operations for
users, roles, profiles, posts, categories, and tags.

The application uses two programs:

- A TCP server that works with the database.
- A command-line client that communicates with the server.

## Requirements

- Python 3.10 or newer.
- A database supported by the SQLAlchemy configuration.

## Installation

Create and activate a virtual environment:

```bash
python -m venv venv
```

On Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the dependencies declared in `pyproject.toml`:

```bash
python -m pip install -e .
```

Configure the database connection using the environment settings expected by
`server/domain/config.py`.

## Running the application

Start the server first:

```bash
python server/server.py
```

Then open a second terminal and start the client:

```bash
python client/app.py
```

The default server address is `127.0.0.1:5000`. Both programs define their
TCP settings directly at the top of their own files (`server/server.py` and
`client/network_client.py`).

## Communication protocol

The client and server exchange UTF-8 encoded JSON through a blocking TCP
socket. A request contains an action in `accion` and its input values in
`datos`:

```json
{
  "accion": "get_user",
  "datos": {
    "id": 1
  }
}
```

A successful response contains `status`, `message`, and `data`:

```json
{
  "status": "ok",
  "message": "User retrieved successfully.",
  "data": {
    "id": 1,
    "username": "student",
    "email": "student@example.com",
    "role_id": 2
  }
}
```

Errors use the same structure with `status` set to `error` and `data` set to
`null`:

```json
{
  "status": "error",
  "message": "The field 'id' must be an integer.",
  "data": null
}
```

See [PROTOCOL.md](PROTOCOL.md) for all supported actions and required fields.

## Tests

The tests use mocks where a database or socket is not needed. Run them from
the project directory:

```bash
python -m pytest tests
```

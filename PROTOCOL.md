# PixelHub communication protocol

## Transport and Security

The client and server communicate asynchronously through non-blocking TCP sockets using Python's `asyncio` framework with hybrid cryptographic security:

- Server address: `127.0.0.1`
- Server port: `5000`
- Character encoding: UTF-8
- Message format: JSON
- Concurrency: Multiple clients are handled concurrently via `asyncio.start_server`.
- **Phase 1 (Handshake):** The client sends its public X.509 certificate (`{"type": "client_hello", "certificate": "<pem>"}`). The server validates the certificate against the trusted Root CA. If valid, the server generates a 256-bit AES session key, encrypts it using the client's public key with **RSA-OAEP**, and sends back `{"status": "ok", "encrypted_session_key": "<hex>"}`.
- **Phase 2 (Encrypted Exchange):** The client decrypts the AES session key using its private key. All application requests and responses are encrypted using **AES-256-GCM** with a fresh 12-byte nonce (`{"nonce": "<hex>", "ciphertext": "<hex>"}`).
- The client signals the end of the request by sending an EOF (`writer.write_eof()`).
- The server reads asynchronously until EOF (`await reader.read()`), decrypts the request, processes it, encrypts the response, drains the transport buffer, and closes the connection cleanly (`writer.close()` and `await writer.wait_closed()`).

## Request format

Every request is a JSON object with two fields:

```json
{
  "accion": "operation_name",
  "datos": {}
}
```

`accion` identifies the operation. `datos` contains the values needed by that
operation. Operations that do not need values use an empty object.

## Response format

Every response is a JSON object with this structure:

```json
{
  "status": "ok",
  "message": "Human-readable result.",
  "data": {}
}
```

The `status` value is either `ok` or `error`. The `message` explains the
result. The `data` field contains the result or `null`.

## Supported operations

### Users

| Action | Required data |
| --- | --- |
| `add_user` | `username`, `email`, `password`, `role_id` |
| `delete_user` | `id` |
| `update_user` | `id`, `attribute`, `new_value` |
| `get_all_users` | None |
| `get_user` | `id` |
| `get_user_by_username` | `username` |
| `get_user_by_email` | `email` |

### Roles

| Action | Required data |
| --- | --- |
| `add_role` | `name`, optional `description` |
| `delete_role` | `id` |
| `update_role` | `id`, `attribute`, `new_value` |
| `get_all_roles` | None |
| `get_role` | `id` |

### Profiles

| Action | Required data |
| --- | --- |
| `add_profile` | `user_id`, `first_name`, `last_name`, `birth_date` |
| `delete_profile` | `id` |
| `update_profile` | `id`, `attribute`, `new_value` |
| `get_all_profiles` | None |
| `get_profile` | `id` |

### Posts

| Action | Required data |
| --- | --- |
| `add_post` | `title`, `category_id`, `user_id`, `content` |
| `delete_post` | `id` |
| `update_post` | `id`, `attribute`, `new_value` |
| `get_all_posts` | None |
| `get_post` | `id` |
| `get_posts_by_category` | `category_id` |
| `get_posts_by_user` | `user_id` |
| `get_last_posts` | None |

### Categories and tags

| Action | Required data |
| --- | --- |
| `add_category` | `name` |
| `delete_category` | `id` |
| `update_category` | `id`, `attribute`, `new_value` |
| `get_all_categories` | None |
| `get_category` | `id` |
| `add_tag` | `name` |
| `delete_tag` | `id` |
| `update_tag` | `id`, `attribute`, `new_value` |
| `get_all_tags` | None |
| `get_tag` | `id` |

### Connection test

The `ping` action checks that the server is reachable:

```json
{
  "accion": "ping",
  "datos": {}
}
```

## Validation and errors

The server validates a request before calling a service. It checks:

- The request is a JSON object.
- `accion` exists and is a supported operation.
- `datos` is an object.
- Required fields are present.
- Identifier fields contain integer values.

If validation fails, the server returns an error response and does not call a
repository or service. Database errors use the same response format.

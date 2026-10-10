import json
import socket


HOST = "127.0.0.1"
PORT = 5000


def send_request(action, payload=None):
    request = {"accion": action, "datos": payload or {}}

    try:
        with socket.create_connection((HOST, PORT), timeout=10) as client_socket:
            client_socket.settimeout(10)
            client_socket.sendall(json.dumps(request).encode("utf-8"))
            client_socket.shutdown(socket.SHUT_WR)

            response_data = bytearray()
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                response_data.extend(chunk)

        if not response_data:
            return {"status": "error", "message": "The server returned an empty response.", "data": None}
        response = json.loads(response_data.decode("utf-8"))
        if not isinstance(response, dict):
            return {"status": "error", "message": "The server returned an invalid response.", "data": None}
        return response
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "error", "message": str(error), "data": None}


if __name__ == "__main__":
    print(send_request("ping"))

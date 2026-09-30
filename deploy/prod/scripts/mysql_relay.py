"""Tiny TCP relay used by the production deploy to reach MySQL through Docker.

The manager's host-level egress to the database is blocked by the surrounding
cloud network, while container traffic on the Docker bridge reaches it (that is
how the running services connect). The deploy workflow starts this script in a
container publishing 127.0.0.1:13306, then runs Flyway against the relay.

Usage: python mysql_relay.py <target-host> <target-port>
"""

import select
import socket
import sys
import threading

LISTEN_PORT = 13306


def pump(client: socket.socket, upstream: socket.socket) -> None:
    try:
        conns = [client, upstream]
        while True:
            readable, _, _ = select.select(conns, [], [])
            for conn in readable:
                data = conn.recv(65536)
                if not data:
                    return
                (upstream if conn is client else client).sendall(data)
    except OSError:
        pass
    finally:
        client.close()
        upstream.close()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: mysql_relay.py <target-host> <target-port>")
    host, port = sys.argv[1], int(sys.argv[2])

    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", LISTEN_PORT))
    server.listen(16)
    print(f"relay listening on {LISTEN_PORT} -> {host}:{port}", flush=True)

    while True:
        client, _ = server.accept()
        try:
            upstream = socket.create_connection((host, port))
        except OSError:
            client.close()
            continue
        threading.Thread(target=pump, args=(client, upstream), daemon=True).start()


if __name__ == "__main__":
    main()

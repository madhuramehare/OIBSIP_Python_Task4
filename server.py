import socket
import threading
import sqlite3
import hashlib
import json

HOST = "127.0.0.1"
PORT = 5555

clients = {}
clients_lock = threading.Lock()

def get_db():
    conn = sqlite3.connect("chat.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            room TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute(
        "INSERT OR IGNORE INTO rooms (name) VALUES (?)",
        ("General",)
    )
    conn.commit()
    return conn
db = get_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_data(client, data):
    try:
        message = json.dumps(data) + "\n"
        client.sendall(message.encode())
    except:
        pass


def broadcast(room, data, exclude=None):
    with clients_lock:
        for client, information in list(clients.items()):
            username, client_room = information

            if client_room == room and client != exclude:
                send_data(client, data)

def handle_client(client):
    username = None

    try:
        while True:
            data = client.recv(4096)

            if not data:
                break

            request = json.loads(data.decode())

            action = request.get("action")
            if action == "register":
                username = request.get("username")
                password = request.get("password")

                if not username or not password:
                    send_data(client, {
                        "action": "response",
                        "success": False,
                        "message": "Username and password are required."
                    })
                    continue

                try:
                    db.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, hash_password(password))
                    )
                    db.commit()

                    send_data(client, {
                        "action": "response",
                        "success": True,
                        "message": "Registration successful."
                    })

                except sqlite3.IntegrityError:
                    send_data(client, {
                        "action": "response",
                        "success": False,
                        "message": "Username already exists."
                    })

            elif action == "login":
                username = request.get("username")
                password = request.get("password")

                cursor = db.execute(
                    "SELECT * FROM users WHERE username=? AND password=?",
                    (username, hash_password(password))
                )

                user = cursor.fetchone()

                if user:
                    with clients_lock:
                        clients[client] = (username, "General")

                    send_data(client, {
                        "action": "login_success",
                        "username": username,
                        "room": "General"
                    })

                    send_room_list(client)
                    send_history(client, "General")

                else:
                    send_data(client, {
                        "action": "response",
                        "success": False,
                        "message": "Invalid username or password."
                    })
            elif action == "get_rooms":
                send_room_list(client)

            elif action == "create_room":
                room = request.get("room")

                if room:
                    try:
                        db.execute(
                            "INSERT INTO rooms (name) VALUES (?)",
                            (room,)
                        )
                        db.commit()

                        send_room_list(client)

                    except sqlite3.IntegrityError:
                        send_data(client, {
                            "action": "response",
                            "success": False,
                            "message": "Room already exists."
                        })


            elif action == "join_room":
                room = request.get("room")

                cursor = db.execute(
                    "SELECT name FROM rooms WHERE name=?",
                    (room,)
                )

                if cursor.fetchone():

                    with clients_lock:
                        if client in clients:
                            clients[client] = (username, room)

                    send_data(client, {
                        "action": "room_joined",
                        "room": room
                    })

                    send_history(client, room)

            elif action == "message":
                message = request.get("message")
                room = request.get("room")

                if username and message:

                    db.execute(
                        "INSERT INTO messages (username, room, message) VALUES (?, ?, ?)",
                        (username, room, message)
                    )
                    db.commit()

                    broadcast(
                        room,
                        {
                            "action": "message",
                            "username": username,
                            "message": message
                        }
                    )

    except Exception as e:
        print("Client error:", e)

    finally:
        with clients_lock:
            if client in clients:
                del clients[client]

        client.close()
        print(username, "disconnected.")
def send_room_list(client):
    cursor = db.execute("SELECT name FROM rooms ORDER BY name")
    rooms = [row[0] for row in cursor.fetchall()]

    send_data(client, {
        "action": "room_list",
        "rooms": rooms
    })
def send_history(client, room):
    cursor = db.execute("""
        SELECT username, message, timestamp
        FROM messages
        WHERE room=?
        ORDER BY id ASC
    """, (room,))

    messages = []

    for username, message, timestamp in cursor.fetchall():
        messages.append({
            "username": username,
            "message": message,
            "timestamp": timestamp
        })

    send_data(client, {
        "action": "history",
        "room": room,
        "messages": messages
    })
def start_server():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))
    server.listen()

    print("=" * 40)
    print("CHAT SERVER STARTED")
    print("Host:", HOST)
    print("Port:", PORT)
    print("=" * 40)

    while True:
        client, address = server.accept()

        print("New connection:", address)

        thread = threading.Thread(
            target=handle_client,
            args=(client,)
        )

        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    start_server()
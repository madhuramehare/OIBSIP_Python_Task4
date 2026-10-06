import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox, simpledialog

HOST = "127.0.0.1"
PORT = 5555

EMOJIS = {
    ":smile:": "😄",
    ":happy:": "😊",
    ":love:": "❤️",
    ":heart:": "❤️",
    ":laugh:": "😂",
    ":sad:": "😢",
    ":angry:": "😠",
    ":thumbsup:": "👍",
    ":ok:": "👌",
    ":fire:": "🔥",
    ":star:": "⭐",
    ":party:": "🥳",
    ":hello:": "👋"
}

def convert_emojis(message):
    for shortcode, emoji in EMOJIS.items():
        message = message.replace(shortcode, emoji)

    return message

class LoginWindow:

    def __init__(self, root):

        self.root = root

        self.root.title("Chat Application - Login")
        self.root.geometry("400x350")

        self.socket = None

        title = tk.Label(
            root,
            text="Chat Application",
            font=("Arial", 22, "bold")
        )

        title.pack(pady=30)

        tk.Label(
            root,
            text="Username"
        ).pack()

        self.username_entry = tk.Entry(
            root,
            width=30
        )

        self.username_entry.pack(pady=5)

        tk.Label(
            root,
            text="Password"
        ).pack()

        self.password_entry = tk.Entry(
            root,
            width=30,
            show="*"
        )

        self.password_entry.pack(pady=5)

        tk.Button(
            root,
            text="Login",
            width=20,
            command=self.login
        ).pack(pady=15)

        tk.Button(
            root,
            text="Register",
            width=20,
            command=self.register
        ).pack()

        self.connect()

    def connect(self):

        try:

            self.socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.socket.connect(
                (HOST, PORT)
            )

            thread = threading.Thread(
                target=self.receive_data
            )

            thread.daemon = True
            thread.start()

        except Exception as e:

            messagebox.showerror(
                "Connection Error",
                "Cannot connect to server.\n"
                "Please start server.py first."
            )

    def send(self, data):

        try:

            message = json.dumps(data) + "\n"

            self.socket.sendall(
                message.encode()
            )

        except:

            messagebox.showerror(
                "Error",
                "Connection lost."
            )

    def register(self):

        username = self.username_entry.get()
        password = self.password_entry.get()

        self.send({
            "action": "register",
            "username": username,
            "password": password
        })
    def login(self):

        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:

            messagebox.showwarning(
                "Warning",
                "Enter username and password."
            )

            return

        self.send({
            "action": "login",
            "username": username,
            "password": password
        })

    def receive_data(self):
        buffer = ""
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split(
                        "\n",
                        1
                                 )
                    if line:
                        response = json.loads(line)
                        self.root.after(
                            0,
                            self.process_response,
                            response
                        )
            except:
                break
    def process_response(self, response):
        action = response.get("action")
        if action == "login_success":
            username = response["username"]
            room = response["room"]
            self.open_chat(
                username,
                room
            )
        elif action == "response":

            if response.get("success"):

                messagebox.showinfo(
                    "Success",
                    response["message"]
                )

            else:

                messagebox.showerror(
                    "Error",
                    response["message"]
                )

    def open_chat(self, username, room):

        self.root.withdraw()

        ChatWindow(
            self.root,
            self.socket,
            username,
            room
        )

class ChatWindow:

    def __init__(
        self,
        root,
        socket_connection,
        username,
        room
    ):

        self.root = root
        self.socket = socket_connection
        self.username = username
        self.room = room

        self.window = tk.Toplevel(root)

        self.window.title(
            f"Chat Application - {username}"
        )

        self.window.geometry(
            "850x600"
        )

        self.create_gui()

        self.receive_thread = threading.Thread(
            target=self.receive_data
        )

        self.receive_thread.daemon = True
        self.receive_thread.start()

        self.get_rooms()
    def create_gui(self):

        # LEFT SIDE
        left_frame = tk.Frame(
            self.window,
            width=200
        )

        left_frame.pack(
            side=tk.LEFT,
            fill=tk.Y
        )

        tk.Label(
            left_frame,
            text="Chat Rooms",
            font=("Arial", 14, "bold")
        ).pack(pady=10)

        self.room_list = tk.Listbox(
            left_frame,
            width=25,
            height=20
        )

        self.room_list.pack(
            padx=10,
            pady=10
        )

        self.room_list.bind(
            "<Double-Button-1>",
            self.join_selected_room
        )

        tk.Button(
            left_frame,
            text="Create Room",
            command=self.create_room
        ).pack(pady=5)

        tk.Button(
            left_frame,
            text="Join Room",
            command=self.join_selected_room
        ).pack(pady=5)

        right_frame = tk.Frame(
            self.window
        )

        right_frame.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True
        )

        self.room_label = tk.Label(
            right_frame,
            text=f"Room: {self.room}",
            font=("Arial", 16, "bold")
        )

        self.room_label.pack(
            pady=10
        )

        self.chat_box = tk.Text(
            right_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Arial", 11)
        )

        self.chat_box.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10
        )

        bottom_frame = tk.Frame(
            right_frame
        )

        bottom_frame.pack(
            fill=tk.X,
            padx=10,
            pady=10
        )

        self.message_entry = tk.Entry(
            bottom_frame,
            font=("Arial", 12)
        )

        self.message_entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True
        )

        self.message_entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        tk.Button(
            bottom_frame,
            text="Send",
            command=self.send_message
        ).pack(
            side=tk.RIGHT,
            padx=5
        )

        tk.Label(
            right_frame,
            text="Emoji shortcuts: :smile: :love: :laugh: :thumbsup: :fire:",
            font=("Arial", 9)
        ).pack(pady=5)

    def send(self, data):

        try:

            message = json.dumps(data) + "\n"

            self.socket.sendall(
                message.encode()
            )

        except:

            messagebox.showerror(
                "Error",
                "Connection lost."
            )

    def send_message(self):

        message = self.message_entry.get().strip()

        if not message:
            return

        self.send({
            "action": "message",
            "room": self.room,
            "message": message
        })

        self.message_entry.delete(
            0,
            tk.END
        )
    def receive_data(self):

        buffer = ""

        while True:

            try:

                data = self.socket.recv(4096)

                if not data:
                    break

                buffer += data.decode()

                while "\n" in buffer:

                    line, buffer = buffer.split(
                        "\n",
                        1
                    )

                    if line:

                        response = json.loads(line)

                        self.window.after(
                            0,
                            self.process_response,
                            response
                        )

            except:

                break

    def process_response(self, response):

        action = response.get("action")

        if action == "message":

            username = response["username"]
            message = response["message"]

            self.add_message(
                username,
                message
            )

            if username != self.username:

                self.show_notification(
                    username,
                    message
                )
        elif action == "history":

            room = response["room"]

            if room == self.room:

                self.clear_chat()

                for item in response["messages"]:

                    self.add_message(
                        item["username"],
                        item["message"],
                        item["timestamp"]
                    )
        elif action == "room_list":

            self.room_list.delete(
                0,
                tk.END
            )

            for room in response["rooms"]:

                self.room_list.insert(
                    tk.END,
                    room
                )

        elif action == "room_joined":

            self.room = response["room"]

            self.room_label.config(
                text=f"Room: {self.room}"
            )

            self.clear_chat()

        elif action == "response":

            if response.get("success"):

                messagebox.showinfo(
                    "Success",
                    response["message"]
                )

                self.get_rooms()

            else:

                messagebox.showerror(
                    "Error",
                    response["message"]
                )
    def add_message(
        self,
        username,
        message,
        timestamp=None
    ):

        message = convert_emojis(
            message
        )

        self.chat_box.config(
            state=tk.NORMAL
        )

        if timestamp:

            self.chat_box.insert(
                tk.END,
                f"[{timestamp}] "
                f"{username}: "
                f"{message}\n"
            )

        else:

            self.chat_box.insert(
                tk.END,
                f"{username}: "
                f"{message}\n"
            )

        self.chat_box.config(
            state=tk.DISABLED
        )

        self.chat_box.see(
            tk.END
        )

    def clear_chat(self):

        self.chat_box.config(
            state=tk.NORMAL
        )

        self.chat_box.delete(
            "1.0",
            tk.END
        )

        self.chat_box.config(
            state=tk.DISABLED
        )
    def get_rooms(self):

        self.send({
            "action": "get_rooms"
        })

    def create_room(self):

        room = simpledialog.askstring(
            "Create Room",
            "Enter room name:"
        )

        if room:

            self.send({
                "action": "create_room",
                "room": room
            })

    def join_selected_room(self):

        selection = self.room_list.curselection()

        if not selection:

            messagebox.showwarning(
                "Warning",
                "Select a room first."
            )

            return

        room = self.room_list.get(
            selection[0]
        )

        self.send({
            "action": "join_room",
            "room": room
        })
    def show_notification(
        self,
        username,
        message
    ):

        try:

            self.window.bell()

            notification = tk.Toplevel(
                self.window
            )

            notification.title(
                "New Message"
            )

            notification.geometry(
                "300x120"
            )

            tk.Label(
                notification,
                text=f"New message from {username}",
                font=("Arial", 12, "bold")
            ).pack(pady=10)

            tk.Label(
                notification,
                text=convert_emojis(message),
                wraplength=250
            ).pack()

            notification.after(
                3000,
                notification.destroy
            )

        except:

            pass

if __name__ == "__main__":

    root = tk.Tk()

    app = LoginWindow(
        root
    )

    root.mainloop()
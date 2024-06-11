from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app)


@app.route("/")
def index():
    return render_template("index.html")


def stream_log():
    log_file = "AM4.log"  # 确保文件路径正确

    with open(log_file, "r") as f:
        f.seek(0,os.SEEK_END)  # 移动到文件开头
        while True:
            line = f.readline()
            if line:
                socketio.emit("log_update", {"data": line})
            else:
                time.sleep(1)  # 暂停1秒再检查新的日志


if __name__ == "__main__":
    log_thread = threading.Thread(target=stream_log, daemon=True)
    log_thread.start()
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)
log_file = "AM4.log"  # 确保文件路径正确
recent_logs = []
recent_logs_num = 20


# 加载最近的日志信息
def load_recent_logs():
    global recent_logs
    with open(log_file, "r") as f:
        lines = f.readlines()
        recent_logs = lines[-recent_logs_num:]


load_recent_logs()


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("connect")
def handle_connect():
    print("Client connected")
    global recent_logs
    # 发送最近的日志信息给客户端
    for line in recent_logs:
        emit("log_update", {"data": line})
    divide = "___________________________________________________\n"
    emit("log_update", {"data": divide})


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")

@app.route('/full_log')
def full_log():
    return render_template('full_log.html')

@app.route('/logs/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(os.getcwd(), filename, as_attachment=True)

def stream_log():
    global recent_logs
    with open(log_file, "r") as f:
        f.seek(0, os.SEEK_END)  # 移动到文件末尾
        while True:
            line = f.readline()
            if line:
                socketio.emit("log_update", {"data": line})
                recent_logs.append(line)
                if len(recent_logs) > recent_logs_num:
                    recent_logs.pop(0)
            else:
                time.sleep(1)  # 暂停1秒再检查新的日志


if __name__ == "__main__":
    socketio.start_background_task(target=stream_log)
    socketio.run(app, host="0.0.0.0", port=8080, debug=True)

from app import create_app, socketio

app = create_app()

if __name__ == "__main__":
    # 0.0.0.0 = reachable from other devices on the same WiFi/LAN
    # (open http://<this-pc's-ip>:5000 on a phone or another laptop)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True,
                 allow_unsafe_werkzeug=True)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO(async_mode="threading")


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object("config.Config")

    db.init_app(app)
    socketio.init_app(app)

    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    from app.routes.auction_routes import auction_bp
    from app.routes.owner import owner_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(auction_bp, url_prefix="/auction")
    app.register_blueprint(owner_bp, url_prefix="/owner")

    from app import auction  # noqa: F401  (registers SocketIO handlers)

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    return app

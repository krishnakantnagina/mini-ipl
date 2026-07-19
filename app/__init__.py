from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object("config.Config")

    db.init_app(app)

    from app.routes.public import public_bp
    from app.routes.admin import admin_bp
    from app.routes.owner import owner_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(owner_bp, url_prefix="/owner")

    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()

    return app

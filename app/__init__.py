from flask import Flask

from app.config import Config
from app.extensions import db



def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Initialize SQLAlchemy
    db.init_app(app)

    # Import models so SQLAlchemy knows about them
    from app.models import User, Document, RAGTrace, RAGEvaluation

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.chat.routes import chat_bp
    from app.documents.routes import documents_bp
    from app.monitoring.routes import monitoring_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(monitoring_bp)

    # Create database and default admin
    with app.app_context():
        db.create_all()
        create_default_admin(app)

    return app


def create_default_admin(app: Flask) -> None:
    from app.models import User

    admin = User.query.filter_by(role="ADMIN").first()

    if admin:
        return

    admin = User(
        username=app.config["DEFAULT_ADMIN_USERNAME"],
        role="ADMIN",
        is_active=True
    )

    admin.set_password(
        app.config["DEFAULT_ADMIN_PASSWORD"]
    )

    db.session.add(admin)
    db.session.commit()

    print(
        f"[AUTH] Default admin created: "
        f"{admin.username}"
    )

from flask import Flask

def create_app() -> Flask:
    app = Flask(__name__)

    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.routes.films import films_bp
    app.register_blueprint(films_bp)

    from app.routes.customers import customers_bp
    app.register_blueprint(customers_bp)

    from app.routes.actors import actors_bp
    app.register_blueprint(actors_bp)

    return app
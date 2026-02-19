from flask import Flask
 
def create_app() -> Flask:
    app = Flask(__name__)

    # Import and register blueprints (routes)
    from app.routes.health import health_bp
    app.register_blueprint(health_bp)

    from app.routes.films import films_bp
    app.register_blueprint(films_bp)

    from app.routes.customers import customers_bp
    app.register_blueprint(customers_bp)

    return app
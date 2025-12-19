from .translate_controller import bp as translate_bp
from .cache_controller import bp as cache_bp


def register_blueprints(app):
    """Register all controller blueprints on the Flask app."""
    app.register_blueprint(translate_bp)
    app.register_blueprint(cache_bp)

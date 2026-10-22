"""RoadSense Vision public API application factory."""
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config

API_PREFIX = "/api/v1"


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from db import db, init_app as init_db

    init_db(app)

    from routes.internal import internal_api
    from routes.public import public_api

    app.register_blueprint(public_api, url_prefix=API_PREFIX)
    app.register_blueprint(internal_api, url_prefix=API_PREFIX)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=86400,
    )

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "error": {
                            "message": "The requested resource was not found.",
                            "status": 404,
                        }
                    }
                ),
                404,
            )
        return (
            jsonify(
                {"error": {"message": "Not found.", "status": 404}}
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return (
            jsonify(
                {
                    "error": {
                        "message": "This endpoint is read-only.",
                        "status": 405,
                    }
                }
            ),
            405,
        )

    @app.errorhandler(413)
    def too_large(_error):
        return (
            jsonify(
                {"error": {"message": "The request payload is too large.", "status": 413}}
            ),
            413,
        )

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("Unhandled API error")
        return (
            jsonify(
                {
                    "error": {
                        "message": "The road condition service encountered an error.",
                        "status": 500,
                    }
                }
            ),
            500,
        )

    @app.cli.command("init-db")
    def init_db_command():
        """Create tables, spatial columns and indexes."""
        from schema import init_database

        init_database(app)
        print("RoadSense database initialised.")

    if app.config.get("AUTO_INIT_DB"):
        try:
            from schema import init_database

            init_database(app)
        except Exception:
            app.logger.exception("Database initialisation failed")
            if not app.config.get("TESTING"):
                raise

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5001, debug=True)

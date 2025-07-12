from flask import Flask
import os


def _register_flow_templates(app):
    """Add templates from each flow to the Jinja search path."""
    flows_dir = os.path.join(os.path.dirname(__file__), "flows")
    if not os.path.isdir(flows_dir):
        return

    for flow_name in os.listdir(flows_dir):
        templates = os.path.join(flows_dir, flow_name, "templates")
        if os.path.isdir(templates) and templates not in app.jinja_loader.searchpath:
            app.jinja_loader.searchpath.append(templates)


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret'

    _register_flow_templates(app)

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app

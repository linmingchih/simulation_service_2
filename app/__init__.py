from flask import Flask
import os
from jinja2 import ChoiceLoader, PrefixLoader, FileSystemLoader
from .translation import translate
from .routes import current_user


def _register_flow_templates(app):
    """Add templates from each flow to the Jinja search path."""
    flows_dir = os.path.join(os.path.dirname(__file__), "flows")
    if not os.path.isdir(flows_dir):
        return

    prefix_map = {}
    for flow_name in os.listdir(flows_dir):
        templates = os.path.join(flows_dir, flow_name, "templates")
        if os.path.isdir(templates):
            prefix_map[flow_name] = FileSystemLoader(templates)

    if prefix_map:
        app.jinja_loader = ChoiceLoader([
            app.jinja_loader,
            PrefixLoader(prefix_map),
        ])


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret'

    _register_flow_templates(app)

    def _t(text):
        user = current_user()
        lang = 'English'
        if user:
            lang = user.get('config', {}).get('language', 'English')
        return translate(text, lang)

    app.jinja_env.globals['t'] = _t

    from .routes import main_bp
    from .admin import admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    return app

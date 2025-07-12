from flask import Blueprint, render_template
from .routes import login_required, admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin_dashboard.html')

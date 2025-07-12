import os
import json
from flask import Blueprint, render_template, request, redirect, url_for
from .routes import (
    login_required,
    admin_required,
    USERS,
    JOB_DIR,
    load_flows,
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin_dashboard.html')


@admin_bp.route('/users', methods=['GET', 'POST'])
@login_required
@admin_required
def users():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        if username and password:
            USERS[username] = {'password': password, 'role': role}
        return redirect(url_for('admin.users'))
    return render_template('user_management.html', users=USERS)


@admin_bp.route('/users/delete/<username>', methods=['POST'])
@login_required
@admin_required
def delete_user(username):
    if username in USERS and username != 'admin':
        USERS.pop(username)
    return redirect(url_for('admin.users'))


@admin_bp.route('/jobs')
@login_required
@admin_required
def jobs():
    jobs_list = []
    if os.path.isdir(JOB_DIR):
        for name in os.listdir(JOB_DIR):
            jdir = os.path.join(JOB_DIR, name)
            if os.path.isdir(jdir):
                info = {'id': name}
                meta_file = os.path.join(jdir, 'metadata.json')
                if os.path.isfile(meta_file):
                    with open(meta_file) as f:
                        try:
                            info.update(json.load(f))
                        except json.JSONDecodeError:
                            pass
                jobs_list.append(info)
    def sort_key(item):
        ts = item.get('created_at')
        try:
            return datetime.fromisoformat(ts) if ts else datetime.min
        except ValueError:
            return datetime.min

    jobs_list.sort(key=sort_key, reverse=True)
    return render_template('jobs_info.html', jobs=jobs_list)


@admin_bp.route('/flows')
@login_required
@admin_required
def flows():
    flows_list = load_flows()
    return render_template('flow_management.html', flows=flows_list)

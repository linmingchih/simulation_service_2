import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for
import shutil
from .routes import (
    login_required,
    admin_required,
    USERS,
    JOB_DIR,
    load_flows,
    load_jobs,
    save_users,
    GROUPS,
    save_groups,
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
            save_users()
        return redirect(url_for('admin.users'))
    return render_template('user_management.html', users=USERS)


@admin_bp.route('/users/delete/<username>', methods=['POST'])
@login_required
@admin_required
def delete_user(username):
    if username in USERS and username != 'admin':
        USERS.pop(username)
        save_users()
    return redirect(url_for('admin.users'))


@admin_bp.route('/jobs')
@login_required
@admin_required
def jobs():
    jobs_list = load_jobs()
    return render_template('jobs_info.html', jobs=jobs_list)


@admin_bp.route('/jobs/delete/<job_id>', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    job_path = os.path.join(JOB_DIR, job_id)
    if os.path.isdir(job_path):
        shutil.rmtree(job_path)
    return redirect(url_for('admin.jobs'))


@admin_bp.route('/flows')
@login_required
@admin_required
def flows():
    flows_list = load_flows()
    return render_template('flow_management.html', flows=flows_list)


@admin_bp.route('/groups', methods=['GET', 'POST'])
@login_required
@admin_required
def groups():
    flows_list = load_flows()
    if request.method == 'POST':
        new_group = request.form.get('group')
        if new_group and new_group not in GROUPS:
            GROUPS[new_group] = []
            save_groups()
        return redirect(url_for('admin.groups'))
    return render_template('group_management.html', groups=GROUPS, flows=flows_list)


@admin_bp.route('/groups/rename/<group>', methods=['POST'])
@login_required
@admin_required
def rename_group(group):
    new_name = request.form.get('new_name')
    if new_name and group in GROUPS and new_name not in GROUPS:
        GROUPS[new_name] = GROUPS.pop(group)
        save_groups()
    return redirect(url_for('admin.groups'))


@admin_bp.route('/groups/delete/<group>', methods=['POST'])
@login_required
@admin_required
def delete_group(group):
    if group in GROUPS:
        GROUPS.pop(group)
        save_groups()
    return redirect(url_for('admin.groups'))


@admin_bp.route('/groups/move', methods=['POST'])
@login_required
@admin_required
def move_flow():
    flow_id = request.form.get('flow_id')
    target = request.form.get('group') or None
    # Remove from all groups
    for g, items in GROUPS.items():
        if flow_id in items:
            items.remove(flow_id)
    if target:
        GROUPS.setdefault(target, []).append(flow_id)
    save_groups()
    return redirect(url_for('admin.groups'))

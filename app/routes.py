import json
import uuid
import os
import shutil
import importlib.util
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOW_DIR = os.path.join(BASE_DIR, 'flows')
JOB_DIR = os.path.join(os.path.dirname(BASE_DIR), 'jobs')
os.makedirs(JOB_DIR, exist_ok=True)

USERS = {
    'admin': {'password': 'admin', 'role': 'admin'},
    'abc': {'password': '1234', 'role': 'user'},
}

main_bp = Blueprint('main', __name__)


def current_user():
    username = session.get('username')
    if username in USERS:
        user = USERS[username].copy()
        user['username'] = username
        return user
    return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user or user.get('role') != 'admin':
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)

    return decorated


def load_flows():
    flows = []
    if not os.path.isdir(FLOW_DIR):
        return flows
    for name in os.listdir(FLOW_DIR):
        fdir = os.path.join(FLOW_DIR, name)
        if os.path.isdir(fdir):
            fjson = os.path.join(fdir, 'flow.json')
            if os.path.isfile(fjson):
                with open(fjson) as f:
                    data = json.load(f)
                    data['id'] = name
                    flows.append(data)
    return flows


def load_jobs():
    jobs = []
    if not os.path.isdir(JOB_DIR):
        return jobs
    for job_id in os.listdir(JOB_DIR):
        jdir = os.path.join(JOB_DIR, job_id)
        if os.path.isdir(jdir):
            meta_file = os.path.join(jdir, 'metadata.json')
            meta = {'id': job_id}
            if os.path.isfile(meta_file):
                with open(meta_file) as f:
                    try:
                        meta.update(json.load(f))
                    except json.JSONDecodeError:
                        pass
            jobs.append(meta)
    def sort_key(item):
        ts = item.get('created_at')
        try:
            return datetime.fromisoformat(ts) if ts else datetime.min
        except ValueError:
            return datetime.min

    jobs.sort(key=sort_key, reverse=True)
    return jobs


@main_bp.route('/')
@login_required
def deck():
    flows = load_flows()
    jobs = load_jobs()
    return render_template('deck.html', flows=flows, jobs=jobs)


@main_bp.route('/flow/<flow_id>/start', methods=['POST'])
@login_required
def start_flow(flow_id):
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOB_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)
    meta = {
        'flow_id': flow_id,
        'created_at': datetime.utcnow().isoformat(),
        'step': 'step_01'
    }
    with open(os.path.join(job_path, 'metadata.json'), 'w') as f:
        json.dump(meta, f)
    return redirect(url_for('main.run_step', flow_id=flow_id, step='step_01', job_id=job_id))


@main_bp.route('/job/<job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    job_path = os.path.join(JOB_DIR, job_id)
    if os.path.isdir(job_path):
        shutil.rmtree(job_path)
    return redirect(url_for('main.deck'))


@main_bp.route('/flow/<flow_id>/<step>/<job_id>', methods=['GET', 'POST'])
@login_required
def run_step(flow_id, step, job_id):
    flow_path = os.path.join(FLOW_DIR, flow_id)
    step_module = os.path.join(flow_path, f'{step}.py')
    if not os.path.isfile(step_module):
        return 'Invalid step', 404
    job_path = os.path.join(JOB_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)
    meta_file = os.path.join(job_path, 'metadata.json')
    meta = {}
    if os.path.isfile(meta_file):
        try:
            with open(meta_file) as f:
                meta = json.load(f)
        except json.JSONDecodeError:
            pass
    meta['step'] = step
    with open(meta_file, 'w') as f:
        json.dump(meta, f)

    if request.method == 'POST':
        # Execute the current step if a run() function exists
        spec = importlib.util.spec_from_file_location(step, step_module)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'run'):
            module.run(job_path, data=request.form)

        # Determine the next step from flow.json
        next_step = None
        flow_json = os.path.join(flow_path, 'flow.json')
        if os.path.isfile(flow_json):
            with open(flow_json) as f:
                data = json.load(f)
                steps = data.get('steps', [])
                if step in steps:
                    idx = steps.index(step)
                    if idx + 1 < len(steps):
                        next_step = steps[idx + 1]

        if next_step:
            return redirect(url_for('main.run_step', flow_id=flow_id, step=next_step, job_id=job_id))
        else:
            return redirect(url_for('main.deck'))

    template = f'steps/{step}.html'
    return render_template(template, flow_id=flow_id, step=step, job_id=job_id)


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = USERS.get(username)
        if user and user.get('password') == password:
            session['username'] = username
            return redirect(url_for('main.deck'))
        error = 'Invalid credentials'
    return render_template('login.html', error=error)


@main_bp.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('main.login'))

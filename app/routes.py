import json
import uuid
import os
import shutil
import importlib.util
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, session, make_response, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOW_DIR = os.path.join(BASE_DIR, 'flows')
JOB_DIR = os.path.join(os.path.dirname(BASE_DIR), 'jobs')
USERS_FILE = os.path.join(os.path.dirname(BASE_DIR), 'users.json')
os.makedirs(JOB_DIR, exist_ok=True)

DEFAULT_USERS = {
    'admin': {'password': 'admin', 'role': 'admin'},
    'abc': {'password': '1234', 'role': 'user'},
}

def _load_users():
    if os.path.isfile(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    # Ensure the file exists with defaults if loading failed
    with open(USERS_FILE, 'w') as f:
        json.dump(DEFAULT_USERS, f)
    return DEFAULT_USERS.copy()


USERS = _load_users()


def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(USERS, f)

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


def parse_timestamp(ts):
    if ts is None:
        return 0
    if isinstance(ts, (int, float)):
        return ts
    if isinstance(ts, str):
        if ts.isdigit():
            return int(ts)
        try:
            return datetime.fromisoformat(ts).timestamp()
        except ValueError:
            try:
                return float(ts)
            except ValueError:
                return 0
    return 0


def format_timestamp(ts):
    if ts is None:
        return ''
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(ts, str):
        if ts.isdigit():
            return datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return ts
    return str(ts)


def _dir_tree(path):
    """Return a formatted directory tree string for the given path."""
    lines = []
    if not os.path.isdir(path):
        return ''
    for root, dirs, files in os.walk(path):
        rel = os.path.relpath(root, path)
        indent = '' if rel == '.' else '    ' * rel.count(os.sep)
        name = '.' if rel == '.' else os.path.basename(root)
        lines.append(f"{indent}{name}/")
        for f in files:
            lines.append(f"{indent}    {f}")
    return '\n'.join(lines)


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


def load_jobs(username=None):
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
            if username is None or meta.get('user') == username:
                jobs.append(meta)
    def sort_key(item):
        return parse_timestamp(item.get('created_at'))

    jobs.sort(key=sort_key, reverse=True)
    for job in jobs:
        job['created_at'] = format_timestamp(job.get('created_at'))
    return jobs


@main_bp.route('/')
@login_required
def deck():
    flows = load_flows()
    user = current_user()
    username = user['username'] if user else None
    jobs = load_jobs(username)
    resp = make_response(render_template('deck.html', flows=flows, jobs=jobs))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@main_bp.route('/flow/<flow_id>/start', methods=['POST'])
@login_required
def start_flow(flow_id):
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOB_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)
    os.makedirs(os.path.join(job_path, 'output'), exist_ok=True)
    user = current_user()
    topic = request.form.get('topic', '').strip()
    meta = {
        'flow_id': flow_id,
        'created_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'step': 'step_01',
        'user': user['username'] if user else '',
        'topic': topic
    }
    with open(os.path.join(job_path, 'metadata.json'), 'w') as f:
        json.dump(meta, f)
    return redirect(url_for('main.run_step', flow_id=flow_id, step='step_01', job_id=job_id))


@main_bp.route('/job/<job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    job_path = os.path.join(JOB_DIR, job_id)
    if os.path.isdir(job_path):
        meta_file = os.path.join(job_path, 'metadata.json')
        owner = None
        if os.path.isfile(meta_file):
            with open(meta_file) as f:
                try:
                    data = json.load(f)
                    owner = data.get('user')
                except json.JSONDecodeError:
                    pass
        user = current_user()
        if user and (user.get('role') == 'admin' or owner == user.get('username')):
            shutil.rmtree(job_path)
    return redirect(url_for('main.deck'))


@main_bp.route('/job/<job_id>/files/<path:filename>')
@login_required
def get_job_file(job_id, filename):
    job_output = os.path.join(JOB_DIR, job_id, 'output')
    if os.path.isfile(os.path.join(job_output, filename)):
        return send_from_directory(job_output, filename, as_attachment=True)
    return 'File not found', 404


@main_bp.route('/flow/<flow_id>/<step>/<job_id>', methods=['GET', 'POST'])
@login_required
def run_step(flow_id, step, job_id):
    flow_path = os.path.join(FLOW_DIR, flow_id)
    step_module = os.path.join(flow_path, f'{step}.py')
    if not os.path.isfile(step_module):
        return 'Invalid step', 404
    job_path = os.path.join(JOB_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)
    os.makedirs(os.path.join(job_path, 'output'), exist_ok=True)
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
            try:
                module.run(job_path, data=request.form, files=request.files)
            except TypeError:
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

    output_dir = os.path.join(job_path, 'output')
    output_files = []
    if os.path.isdir(output_dir):
        for f in os.listdir(output_dir):
            if os.path.isfile(os.path.join(output_dir, f)):
                output_files.append(f)

    input_tree = _dir_tree(os.path.join(job_path, 'input'))
    output_tree = _dir_tree(output_dir)

    template = f'{flow_id}/steps/{step}.html'
    return render_template(
        template,
        flow_id=flow_id,
        step=step,
        job_id=job_id,
        output_files=output_files,
        input_tree=input_tree,
        output_tree=output_tree,
    )


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

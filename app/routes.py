import json
import uuid
import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOW_DIR = os.path.join(BASE_DIR, 'flows')
JOB_DIR = os.path.join(os.path.dirname(BASE_DIR), 'jobs')

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


@main_bp.route('/')
@login_required
def deck():
    flows = load_flows()
    return render_template('deck.html', flows=flows)


@main_bp.route('/flow/<flow_id>/start', methods=['POST'])
@login_required
def start_flow(flow_id):
    job_id = str(uuid.uuid4())
    job_path = os.path.join(JOB_DIR, job_id)
    os.makedirs(job_path, exist_ok=True)

    return redirect(url_for('main.run_step', flow_id=flow_id, step='step_01', job_id=job_id))


@main_bp.route('/flow/<flow_id>/<step>/<job_id>', methods=['GET', 'POST'])
@login_required
def run_step(flow_id, step, job_id):
    flow_path = os.path.join(FLOW_DIR, flow_id)
    step_module = os.path.join(flow_path, f'{step}.py')
    if not os.path.isfile(step_module):
        return 'Invalid step', 404

    if request.method == 'POST':
        # Here we would process form data and execute the step
        pass

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

import json
import uuid
import os
import importlib.util
import zipfile
from app.utils import remove_dir
from pyedb import Edb
from collections import defaultdict
from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, session, make_response, send_from_directory, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLOW_DIR = os.path.join(BASE_DIR, 'flows')
JOB_DIR = os.path.join(os.path.dirname(BASE_DIR), 'jobs')
USERS_FILE = os.path.join(os.path.dirname(BASE_DIR), 'users.json')
GROUPS_FILE = os.path.join(os.path.dirname(BASE_DIR), 'groups.json')
os.makedirs(JOB_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    'aedt_version': '2025.1',
    'edb_version': '2024.1',
    'language': 'English',
    'scheme': 'Light',
}


def _default_config():
    return DEFAULT_CONFIG.copy()


DEFAULT_USERS = {
    'admin': {'password': 'admin', 'role': 'admin', 'config': _default_config()},
    'abc': {'password': '1234', 'role': 'user', 'config': _default_config()},
}

DEFAULT_GROUPS = {
    'SIwave': ['Flow_SIwave_SYZ'],
    'HFSS': ['Flow_Dummy', 'Flow_Example']
}

def _load_users():
    if os.path.isfile(USERS_FILE):
        try:
            with open(USERS_FILE) as f:
                data = json.load(f)
                for u in data.values():
                    cfg = u.get('config')
                    if not isinstance(cfg, dict):
                        u['config'] = _default_config()
                    else:
                        for k, v in DEFAULT_CONFIG.items():
                            cfg.setdefault(k, v)
                return data
        except json.JSONDecodeError:
            pass
    # Ensure the file exists with defaults if loading failed
    with open(USERS_FILE, 'w') as f:
        json.dump(DEFAULT_USERS, f)
    return DEFAULT_USERS.copy()


USERS = _load_users()


def _load_groups():
    if os.path.isfile(GROUPS_FILE):
        try:
            with open(GROUPS_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    with open(GROUPS_FILE, 'w') as f:
        json.dump(DEFAULT_GROUPS, f)
    return DEFAULT_GROUPS.copy()


GROUPS = _load_groups()


def save_groups():
    with open(GROUPS_FILE, 'w') as f:
        json.dump(GROUPS, f)


def save_users():
    with open(USERS_FILE, 'w') as f:
        json.dump(USERS, f, indent=2)


def _ensure_user_config(username):
    user = USERS.get(username)
    if not user:
        return
    cfg = user.get('config')
    if not isinstance(cfg, dict):
        user['config'] = _default_config()
    else:
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)

main_bp = Blueprint('main', __name__)


def current_user():
    username = session.get('username')
    if username in USERS:
        _ensure_user_config(username)
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
                    # Determine group
                    group = None
                    for gname, items in GROUPS.items():
                        if name in items:
                            group = gname
                            break
                    data['group'] = group
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
    groups = sorted(GROUPS.keys())
    # Determine selected group from query parameter for server-side filtering
    selected_group = request.args.get('group', 'all')
    if selected_group != 'all':
        if selected_group == 'Ungrouped':
            flows = [f for f in flows if not f.get('group')]
        else:
            flows = [f for f in flows if f.get('group') == selected_group]
    user = current_user()
    username = user['username'] if user else None
    jobs = load_jobs(username)
    resp = make_response(render_template('deck.html', flows=flows, jobs=jobs, groups=groups,
                                         selected_group=selected_group))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp


@main_bp.route('/api/jobs')
@login_required
def api_jobs():
    """Return jobs for the current user as JSON."""
    user = current_user()
    username = user['username'] if user else None
    jobs = load_jobs(username)
    return jsonify({'jobs': jobs})


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
            remove_dir(job_path)
    return redirect(url_for('main.deck'))


@main_bp.route('/job/<job_id>/files/<path:filename>')
@login_required
def get_job_file(job_id, filename):
    """Return a file from a job's output or input directory."""
    job_output = os.path.join(JOB_DIR, job_id, 'output')
    job_input = os.path.join(JOB_DIR, job_id, 'input')
    if os.path.isfile(os.path.join(job_output, filename)):
        return send_from_directory(job_output, filename, as_attachment=True)
    if os.path.isfile(os.path.join(job_input, filename)):
        return send_from_directory(job_input, filename, as_attachment=True)
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
    user = current_user()
    cfg = user.get('config', {}) if user else {}
    edb_version = cfg.get('edb_version', '2024.1')
    meta_file = os.path.join(job_path, 'metadata.json')
    meta = {}
    if os.path.isfile(meta_file):
        try:
            with open(meta_file) as f:
                meta = json.load(f)
        except json.JSONDecodeError:
            pass

    flow_json = os.path.join(flow_path, 'flow.json')
    flow_name = flow_id
    if os.path.isfile(flow_json):
        try:
            with open(flow_json) as f:
                data = json.load(f)
                flow_name = data.get('name', flow_id)
        except json.JSONDecodeError:
            pass

    job_topic = meta.get('topic', '')


    current_step = meta.get('step', step)

    if current_step == 'completed':
        return redirect(url_for('main.deck'))

    if step != current_step:
        return redirect(url_for('main.run_step', flow_id=flow_id, step=current_step, job_id=job_id))


    if request.method == 'POST':
        action = request.form.get('action')
        if action != 'pass':
            # Execute the current step if a run() function exists
            spec = importlib.util.spec_from_file_location(step, step_module)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'run'):
                try:
                    module.run(job_path, data=request.form, files=request.files, config=cfg)
                except TypeError:
                    try:
                        module.run(job_path, data=request.form, config=cfg)
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
            meta['step'] = next_step
        else:
            meta['step'] = 'completed'
        with open(meta_file, 'w') as f:
            json.dump(meta, f)

        if next_step:
            return redirect(url_for('main.run_step', flow_id=flow_id, step=next_step, job_id=job_id))
        else:
            return redirect(url_for('main.deck'))

    output_dir = os.path.join(job_path, 'output')
    if flow_id == 'Flow_SIwave_SYZ' and step == 'step_05':
        edb_dir = os.path.join(output_dir, 'design.aedb')
        zip_path = os.path.join(output_dir, 'design.aedb.zip')
        if os.path.isdir(edb_dir) and not os.path.isfile(zip_path):
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(edb_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, os.path.dirname(edb_dir))
                        zf.write(abs_path, rel_path)
    output_files = []
    if os.path.isdir(output_dir):
        for f in os.listdir(output_dir):
            if os.path.isfile(os.path.join(output_dir, f)):
                output_files.append(f)

    info_lines = None
    nets = None
    selected_nets = None
    zip_file = None
    if flow_id == 'Flow_SIwave_SYZ' and step == 'step_02':
        design_file = None
        input_dir = os.path.join(job_path, 'input')
        if os.path.isdir(input_dir):
            for f in os.listdir(input_dir):
                if f.lower().endswith(('.brd', '.zip', '.aedb')):
                    design_file = f
                    break
        xlsx_file = 'stackup.xlsx' if os.path.isfile(os.path.join(output_dir, 'stackup.xlsx')) else None
        info_lines = []
        if design_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=design_file)
            info_lines.append(f'Step 1 Input: <a href="{url}" download>{design_file}</a>')
        if xlsx_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=xlsx_file)
            info_lines.append(f'Step 1 Output: <a href="{url}" download>{xlsx_file}</a>')
    elif flow_id == 'Flow_SIwave_SYZ' and step == 'step_03':
        categories = {}
        renamed_map = {}
        edb_dir = os.path.join(output_dir, 'design.aedb')
        if os.path.isdir(edb_dir):
            try:
                edb = Edb(edb_dir, edbversion=edb_version)
                type_part = defaultdict(set)
                for cname, comp in edb.components.components.items():
                    type_part[comp.type].add(comp.part_name)
                categories = {
                    'IC Parts': sorted(type_part.get('IC', [])),
                    'IO Parts': sorted(type_part.get('IO', [])),
                    'Other Parts': sorted(type_part.get('Other', [])),
                }
                edb.close_edb()
            except Exception:
                categories = {}
        rename_file = os.path.join(output_dir, 'renamed_components.json')
        if os.path.isfile(rename_file):
            try:
                with open(rename_file) as fp:
                    renamed_map = json.load(fp)
            except json.JSONDecodeError:
                renamed_map = {}
        nets = None
        info_lines = []
        design_file = None
        xlsx_input = None
        input_dir = os.path.join(job_path, 'input')
        if os.path.isdir(input_dir):
            for f in os.listdir(input_dir):
                if f.lower().endswith(('.brd', '.zip', '.aedb')) and not design_file:
                    design_file = f
                if f.lower().endswith('.xlsx'):
                    xlsx_input = f
        stackup_file = 'stackup.xlsx' if os.path.isfile(os.path.join(output_dir, 'stackup.xlsx')) else None
        if design_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=design_file)
            info_lines.append(f'Step 1 Input: <a href="{url}" download>{design_file}</a>')
        if stackup_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=stackup_file)
            info_lines.append(f'Step 1 Output: <a href="{url}" download>{stackup_file}</a>')
        if xlsx_input:
            url = url_for('main.get_job_file', job_id=job_id, filename=xlsx_input)
            info_lines.append(f'Step 2 Input: <a href="{url}" download>{xlsx_input}</a>')
    elif flow_id == 'Flow_SIwave_SYZ' and step == 'step_04':
        design_file = None
        xlsx_input = None
        input_dir = os.path.join(job_path, 'input')
        if os.path.isdir(input_dir):
            for f in os.listdir(input_dir):
                if f.lower().endswith(('.brd', '.zip', '.aedb')) and not design_file:
                    design_file = f
                if f.lower().endswith('.xlsx'):
                    xlsx_input = f
        stackup_file = 'stackup.xlsx' if os.path.isfile(os.path.join(output_dir, 'stackup.xlsx')) else None
        updated_file = 'updated.xlsx' if os.path.isfile(os.path.join(output_dir, 'updated.xlsx')) else None
        zipped_file = 'updated_pyedb.zip' if os.path.isfile(os.path.join(output_dir, 'updated_pyedb.zip')) else None
        info_lines = []
        if design_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=design_file)
            info_lines.append(f'Step 1 Input: <a href="{url}" download>{design_file}</a>')
        if stackup_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=stackup_file)
            info_lines.append(f'Step 1 Output: <a href="{url}" download>{stackup_file}</a>')
        if xlsx_input:
            url = url_for('main.get_job_file', job_id=job_id, filename=xlsx_input)
            info_lines.append(f'Step 2 Input: <a href="{url}" download>{xlsx_input}</a>')
        if zipped_file:
            url = url_for('main.get_job_file', job_id=job_id, filename=zipped_file)
            info_lines.append(f'Step 2 Output: <a href="{url}" download>{zipped_file}</a>')

        nets = []
        edb_dir = os.path.join(output_dir, 'design.aedb')
        if os.path.isdir(edb_dir):
            try:
                edb = Edb(edb_dir, edbversion=edb_version)
                nets = list(edb.nets.nets.keys())
                edb.close_edb()
            except Exception:
                nets = []
    elif flow_id == 'Flow_SIwave_SYZ' and step == 'step_05':
        cutout_zip = 'cutout.zip' if os.path.isfile(os.path.join(output_dir, 'cutout.zip')) else None
        design_zip = 'design.aedb.zip' if os.path.isfile(os.path.join(output_dir, 'design.aedb.zip')) else None
        nets = None
        info_lines = []
        for zf in (cutout_zip, design_zip):
            if zf:
                url = url_for('main.get_job_file', job_id=job_id, filename=zf)
                info_lines.append(f'<strong>Output:</strong> <a href="{url}" download>{zf}</a>')

    else:
        nets = None

    input_tree = _dir_tree(os.path.join(job_path, 'input'))
    output_tree = _dir_tree(output_dir)

    template = f'{flow_id}/steps/{step}.html'
    return render_template(
        template,
        flow_id=flow_id,
        flow_name=flow_name,
        step=step,
        job_id=job_id,
        job_topic=job_topic,
        output_files=output_files,
        info_lines=info_lines,
        nets=nets,
        input_tree=input_tree,
        output_tree=output_tree,
        selected_nets=selected_nets,
        zip_file=zip_file,
        categories=locals().get('categories'),
        renamed_map=locals().get('renamed_map'),
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


@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def user_config():
    user = current_user()
    username = user['username']
    cfg = USERS[username].setdefault('config', _default_config())
    if request.method == 'POST':
        cfg['aedt_version'] = request.form.get('aedt_version', cfg['aedt_version']).strip()
        cfg['edb_version'] = request.form.get('edb_version', cfg['edb_version']).strip()
        cfg['language'] = request.form.get('language', cfg['language'])
        cfg['scheme'] = request.form.get('scheme', cfg['scheme'])
        save_users()
        return redirect(url_for('main.user_config'))
    return render_template('user_config.html', config=cfg)

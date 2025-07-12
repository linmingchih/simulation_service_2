import os
import shutil


def run(job_path, data=None, files=None):
    input_dir = os.path.join(job_path, 'input')
    output_dir = os.path.join(job_path, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    xlsx = files.get('xlsx_file') if files else None
    if xlsx and xlsx.filename:
        x_path = os.path.join(input_dir, xlsx.filename)
        xlsx.save(x_path)
        shutil.copy(x_path, os.path.join(output_dir, 'updated.xlsx'))

    return {}

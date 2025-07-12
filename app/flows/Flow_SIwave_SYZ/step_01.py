import os
from openpyxl import Workbook


def run(job_path, data=None, files=None):
    input_dir = os.path.join(job_path, 'input')
    output_dir = os.path.join(job_path, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    brd = files.get('brd_file') if files else None
    if brd and brd.filename:
        brd_path = os.path.join(input_dir, brd.filename)
        brd.save(brd_path)

        # Placeholder for conversion to EDB
        edb_dir = os.path.join(output_dir, 'design.aedb')
        os.makedirs(edb_dir, exist_ok=True)
        with open(os.path.join(edb_dir, 'placeholder.txt'), 'w') as f:
            f.write('EDB content')

        # Generate a simple stackup.xlsx
        xlsx_path = os.path.join(output_dir, 'stackup.xlsx')
        wb = Workbook()
        ws = wb.active
        ws.title = 'Stackup'
        ws.append(['Layer Name', 'Type', 'Thickness (mm)', 'Permittivity', 'Loss Tangent', 'Conductivity (S/m)'])
        wb.save(xlsx_path)

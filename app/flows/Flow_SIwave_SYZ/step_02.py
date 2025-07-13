import os
import shutil
import zipfile
import openpyxl
from pyedb import Edb


def apply_xlsx(xlsx_path, edb_path):
    edb = Edb(edb_path, edbversion="2024.1")
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb["Stackup"]
    for row in ws.iter_rows(min_row=2, values_only=True):
        layer_name, layer_type, thickness_mm, permittivity, loss_tangent, conductivity = row
        thickness_m = float(thickness_mm) / 1000.0
        edb.stackup.stackup_layers[layer_name].thickness = thickness_m
        mat_name = edb.stackup.stackup_layers[layer_name].material
        material = edb.materials.materials[mat_name]
        if layer_type != "signal":
            if permittivity != "":
                material.permittivity = float(permittivity)
            if loss_tangent != "":
                material.dielectric_loss_tangent = float(loss_tangent)
        else:
            if conductivity != "":
                material.conductivity = float(conductivity)
    edb.save_edb()
    edb.close_edb()


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

        edb_dir = os.path.join(output_dir, 'design.aedb')
        if os.path.isdir(edb_dir):
            apply_xlsx(x_path, edb_dir)

            # Create a zipped copy of the updated AEDB for easy download
            zip_path = os.path.join(output_dir, 'updated_pyedb.zip')
            if os.path.isfile(zip_path):
                os.remove(zip_path)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(edb_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, os.path.dirname(edb_dir))
                        zf.write(abs_path, rel_path)

    return {}

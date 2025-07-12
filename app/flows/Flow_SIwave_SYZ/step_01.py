import os
import shutil
import stat
from openpyxl import Workbook
from pyedb import Edb


def export_stackup(edb_obj, xlsx_path):
    data = []
    for layer_name, layer in edb_obj.stackup.stackup_layers.items():
        mat = edb_obj.materials.materials[layer.material]
        if layer.type == "signal":
            permittivity = ""
            loss_tangent = ""
            conductivity = mat.conductivity
        else:
            permittivity = mat.permittivity
            loss_tangent = mat.dielectric_loss_tangent
            conductivity = ""
        thickness_mm = layer.thickness * 1000.0
        data.append(
            [
                layer_name,
                layer.type,
                thickness_mm,
                permittivity,
                loss_tangent,
                conductivity,
            ]
        )
    wb = Workbook()
    ws = wb.active
    ws.title = "Stackup"
    header = [
        "Layer Name",
        "Type",
        "Thickness (mm)",
        "Permittivity",
        "Loss Tangent",
        "Conductivity (S/m)",
    ]
    ws.append(header)
    for row in data:
        ws.append(row)
    wb.save(xlsx_path)


def _remove_dir(path):
    """Remove directory and handle read-only files on Windows."""
    def _onerror(func, target, exc):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            pass

    if os.path.isdir(path):
        shutil.rmtree(path, onerror=_onerror)


def run(job_path, data=None, files=None):
    input_dir = os.path.join(job_path, 'input')
    output_dir = os.path.join(job_path, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    brd = files.get("brd_file") if files else None
    if brd and brd.filename:
        brd_path = os.path.join(input_dir, brd.filename)
        brd.save(brd_path)

        # Convert the BRD file to an AEDB using PyEDB
        edb = Edb(brd_path, edbversion="2024.1")
        edb_dir = os.path.join(output_dir, "design.aedb")
        _remove_dir(edb_dir)
        edb.save_as(edb_dir)

        # Export the stackup to Excel
        xlsx_path = os.path.join(output_dir, "stackup.xlsx")
        export_stackup(edb, xlsx_path)
        edb.close()

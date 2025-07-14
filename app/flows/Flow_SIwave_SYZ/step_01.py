import os
import shutil
from app.utils import remove_dir
from openpyxl import Workbook
from pyedb import Edb


def export_stackup(edb_obj, xlsx_path, unit="mm"):
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
        if unit == "mil":
            thickness = layer.thickness * 1000.0 / 0.0254
        else:
            thickness = layer.thickness * 1000.0
        data.append(
            [
                layer_name,
                layer.type,
                thickness,
                permittivity,
                loss_tangent,
                conductivity,
            ]
        )
    wb = Workbook()
    ws = wb.active
    ws.title = "Stackup"
    ws.append(["unit", unit])
    header = [
        "Layer Name",
        "Type",
        f"Thickness ({unit})",
        "Permittivity",
        "Loss Tangent",
        "Conductivity (S/m)",
    ]
    ws.append(header)
    for row in data:
        ws.append(row)
    wb.save(xlsx_path)




def run(job_path, data=None, files=None):
    input_dir = os.path.join(job_path, 'input')
    output_dir = os.path.join(job_path, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    unit = "mm"
    if data:
        unit = data.get("unit", "mm")
    brd = files.get("brd_file") if files else None
    aedb_files = files.getlist("aedb_folder") if files else []
    if brd and brd.filename:
        brd_path = os.path.join(input_dir, brd.filename)
        brd.save(brd_path)

        # Convert the BRD file to an AEDB using PyEDB
        edb = Edb(brd_path, edbversion="2024.1")
        edb_dir = os.path.join(output_dir, "design.aedb")
        remove_dir(edb_dir)
        edb.save_as(edb_dir)

        # Export the stackup to Excel
        xlsx_path = os.path.join(output_dir, "stackup.xlsx")
        export_stackup(edb, xlsx_path, unit=unit)
        edb.close()
    elif aedb_files and any(f.filename for f in aedb_files):
        aedb_input = os.path.join(input_dir, "uploaded.aedb")
        remove_dir(aedb_input)
        for f in aedb_files:
            if not f.filename:
                continue
            dest = os.path.join(aedb_input, f.filename)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            f.save(dest)

        edb_dir = os.path.join(output_dir, "design.aedb")
        remove_dir(edb_dir)
        shutil.copytree(aedb_input, edb_dir)

        edb = Edb(edb_dir, edbversion="2024.1")
        xlsx_path = os.path.join(output_dir, "stackup.xlsx")
        export_stackup(edb, xlsx_path, unit=unit)
        edb.close()

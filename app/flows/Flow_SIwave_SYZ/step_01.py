import os
import shutil
import zipfile
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




def run(job_path, data=None, files=None, config=None):
    input_dir = os.path.join(job_path, 'input')
    output_dir = os.path.join(job_path, 'output')
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    unit = "mm"
    if data:
        unit = data.get("unit", "mm")
    design = files.get("design_file") if files else None
    edb_version = (config or {}).get("edb_version", "2024.1")
    if design and design.filename:
        filename = design.filename
        ext = os.path.splitext(filename)[1].lower()
        design_path = os.path.join(input_dir, filename)
        design.save(design_path)

        if ext == ".brd":
            edb = Edb(design_path, edbversion=edb_version)
            edb_dir = os.path.join(output_dir, "design.aedb")
            remove_dir(edb_dir)
            edb.save_as(edb_dir)

            with open(os.path.join(output_dir, "rename.log"), "w") as fp:
                fp.write("BRD converted to design.aedb\n")

            xlsx_path = os.path.join(output_dir, "stackup.xlsx")
            export_stackup(edb, xlsx_path, unit=unit)

            # Plot all signal layers for the next step carousel
            try:
                for layer_name in edb.stackup.signal_layers:
                    img_path = os.path.join(output_dir, f"{layer_name}.png")
                    edb.nets.plot(layers=[layer_name], show=False, save_plot=img_path)
            except Exception as e:
                with open(os.path.join(output_dir, "plot_error.log"), "a") as fp:
                    fp.write(f"Failed to plot {layer_name}: {e}\n")

            edb.close()
        else:
            tmp_dir = os.path.join(input_dir, "aedb_zip")
            remove_dir(tmp_dir)
            os.makedirs(tmp_dir, exist_ok=True)
            with zipfile.ZipFile(design_path) as zf:
                zf.extractall(tmp_dir)

            aedb_folder = None
            for name in os.listdir(tmp_dir):
                p = os.path.join(tmp_dir, name)
                if name.lower().endswith(".aedb") and os.path.isdir(p):
                    aedb_folder = p
                    break
            if not aedb_folder:
                aedb_folder = tmp_dir

            edb_dir = os.path.join(output_dir, "design.aedb")
            remove_dir(edb_dir)
            shutil.copytree(aedb_folder, edb_dir)

            with open(os.path.join(output_dir, "rename.log"), "w") as fp:
                fp.write(f"Uploaded {filename} extracted to design.aedb\n")

            edb = Edb(edb_dir, edbversion=edb_version)
            xlsx_path = os.path.join(output_dir, "stackup.xlsx")
            export_stackup(edb, xlsx_path, unit=unit)

            # Plot all signal layers for the next step carousel
            try:
                for layer_name in edb.stackup.signal_layers:
                    img_path = os.path.join(output_dir, f"{layer_name}.png")
                    edb.nets.plot(layers=[layer_name], show=False, save_plot=img_path)
            except Exception as e:
                with open(os.path.join(output_dir, "plot_error.log"), "a") as fp:
                    fp.write(f"Failed to plot {layer_name}: {e}\n")

            edb.close()

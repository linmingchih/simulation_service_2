import os
import json
import zipfile
from app.utils import remove_dir
from pyedb import Edb




def run(job_path, data=None, files=None, config=None):
    output_dir = os.path.join(job_path, "output")
    os.makedirs(output_dir, exist_ok=True)

    edb_dir = os.path.join(output_dir, "design.aedb")
    if not os.path.isdir(edb_dir):
        return {}

    edb_version = (config or {}).get("edb_version", "2024.1")
    edb = Edb(edb_dir, edbversion=edb_version)
    all_nets = list(edb.nets.nets.keys())

    selected_nets = []
    pwr_nets = []
    if data:
        for net in all_nets:
            if data.get(f"import_{net}"):
                selected_nets.append(net)
            if data.get(f"pwr_{net}"):
                pwr_nets.append(net)

    if selected_nets:
        cutout_dir = os.path.join(output_dir, "cutout.aedb")
        remove_dir(cutout_dir)
        edb.cutout(
            signal_list=selected_nets,
            reference_list=pwr_nets,
            extent_type="Bounding",
            output_aedb_path=cutout_dir,
            open_cutout_at_end=False,
        )

        zip_path = os.path.join(output_dir, "cutout.zip")
        if os.path.isfile(zip_path):
            os.remove(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(cutout_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, os.path.dirname(cutout_dir))
                    zf.write(abs_path, rel_path)

    edb.close_edb()

    with open(os.path.join(output_dir, "cutout_info.json"), "w") as fp:
        json.dump({"selected_nets": selected_nets, "pwr_nets": pwr_nets}, fp)

    return {}

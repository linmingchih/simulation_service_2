import os
import json
from pyedb import Edb


def change_name(edb_obj, old_name, new_name):
    """Rename a component definition inside the EDB."""
    for comp_def in edb_obj.component_defs:
        if comp_def.GetName() == old_name:
            comp_def.SetName(new_name)
            return True
    return False


def run(job_path, data=None, files=None, config=None):
    output_dir = os.path.join(job_path, "output")
    edb_dir = os.path.join(output_dir, "design.aedb")
    if not os.path.isdir(edb_dir):
        return {}

    rename_log = {}
    edb_version = (config or {}).get("edb_version", "2024.1")
    edb = Edb(edb_dir, edbversion=edb_version)
    if data:
        for _, comp in edb.components.components.items():
            new_name = data.get(f"new_{comp.part_name}")
            if new_name and new_name != comp.part_name:
                if change_name(edb, comp.part_name, new_name):
                    rename_log[comp.part_name] = new_name
        if rename_log:
            edb.save()
    edb.close_edb()

    if rename_log:
        with open(os.path.join(output_dir, "renamed_components.json"), "w") as fp:
            json.dump(rename_log, fp)
    return {}

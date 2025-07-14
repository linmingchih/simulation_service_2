import os
import json
from collections import defaultdict
from pyedb import Edb


def run(job_path, data=None, files=None):
    output_dir = os.path.join(job_path, "output")
    edb_dir = os.path.join(output_dir, "design.aedb")
    if not os.path.isdir(edb_dir):
        return {}

    rename_log = {}
    edb = Edb(edb_dir, edbversion="2024.1")
    if data:
        for comp_name, comp in edb.components.components.items():
            new_name = data.get(f"new_{comp.part_name}")
            if new_name and new_name != comp.part_name:
                for comp_def in edb.component_defs:
                    if comp_def.GetName() == comp.part_name:
                        comp_def.SetName(new_name)
                        rename_log[comp.part_name] = new_name
                        break
        if rename_log:
            edb.save()
    edb.close_edb()

    if rename_log:
        with open(os.path.join(output_dir, "renamed_components.json"), "w") as fp:
            json.dump(rename_log, fp)
    return {}

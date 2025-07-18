import os
import json
from collections import defaultdict
from pyedb import Edb


def run(job_path, data=None, files=None, config=None):
    output_dir = os.path.join(job_path, "output")
    cutout_dir = os.path.join(output_dir, "cutout.aedb")
    edb_dir = cutout_dir if os.path.isdir(cutout_dir) else os.path.join(output_dir, "design.aedb")
    if not os.path.isdir(edb_dir):
        return {}

    edb_version = (config or {}).get("edb_version", "2024.1")
    edb = Edb(edb_dir, edbversion=edb_version)

    info = defaultdict(list)
    for net_name, net in edb.nets.nets.items():
        for ref_des, comp in net.components.items():
            for pin_name, pin in comp.pins.items():
                info[net_name].append([pin_name, ref_des, comp.part_name])

    selected = []
    if data:
        for net_name, pins in info.items():
            for idx, pin in enumerate(pins):
                if data.get(f"port_{net_name}_{idx}"):
                    selected.append({
                        "net": net_name,
                        "pin_name": pin[0],
                        "ref_des": pin[1],
                        "part_name": pin[2],
                    })
        if selected:
            with open(os.path.join(output_dir, "selected_ports.json"), "w") as fp:
                json.dump(selected, fp)

    edb.close_edb()
    return {}

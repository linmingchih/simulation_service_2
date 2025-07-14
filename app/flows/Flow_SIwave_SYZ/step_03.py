import os
import json
from pyedb import Edb


def run(job_path, data=None, files=None):
    output_dir = os.path.join(job_path, "output")
    os.makedirs(output_dir, exist_ok=True)

    nets = []
    edb_dir = os.path.join(output_dir, "design.aedb")
    if os.path.isdir(edb_dir):
        try:
            edb = Edb(edb_dir, edbversion="2024.1")
            nets = list(edb.nets.nets.keys())
            edb.close_edb()
        except Exception:
            nets = []

    with open(os.path.join(output_dir, "nets.json"), "w") as fp:
        json.dump({"nets": nets}, fp)

    return {}

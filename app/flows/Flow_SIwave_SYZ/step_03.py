import os
import json


def run(job_path, data=None, files=None):
    output_dir = os.path.join(job_path, "output")
    os.makedirs(output_dir, exist_ok=True)

    file_list = []
    for f in os.listdir(output_dir):
        p = os.path.join(output_dir, f)
        if os.path.isfile(p):
            file_list.append(f)
    summary = {"output_files": file_list}
    with open(os.path.join(output_dir, "summary.json"), "w") as fp:
        json.dump(summary, fp)

    return {}

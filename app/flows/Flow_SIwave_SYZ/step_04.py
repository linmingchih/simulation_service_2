import os
import json
import re
from pyedb import Edb


def _get_comp_value(comp):
    """Return the component value depending on its type."""
    if comp.type == "Resistor" and hasattr(comp, "res_value"):
        return comp.res_value
    if comp.type == "Capacitor" and hasattr(comp, "cap_value"):
        return comp.cap_value
    if comp.type == "Inductor" and hasattr(comp, "ind_value"):
        return comp.ind_value
    return comp.value


def _set_comp_value(comp, value):
    """Set the component value depending on its type."""
    if comp.type == "Resistor" and hasattr(comp, "res_value"):
        comp.res_value = value
    elif comp.type == "Capacitor" and hasattr(comp, "cap_value"):
        comp.cap_value = value
    elif comp.type == "Inductor" and hasattr(comp, "ind_value"):
        comp.ind_value = value
    else:
        comp.value = value

def normalize_value(value_str):
    """Normalize user entered value strings to EDG standard format."""
    if value_str is None:
        return None
    value_str = value_str.replace("Ω", "ohm").replace("µ", "u").strip().lower()
    match = re.match(r"([\d.]+)\s*([a-z]+)?", value_str)
    if not match:
        return None
    val, unit = match.groups()
    return f"{val}{unit or ''}"


def run(job_path, data=None, files=None, config=None):
    output_dir = os.path.join(job_path, "output")
    edb_dir = os.path.join(output_dir, "design.aedb")
    if not os.path.isdir(edb_dir):
        return {}

    edb_version = (config or {}).get("edb_version", "2024.1")
    edb = Edb(edb_dir, edbversion=edb_version)

    changes = {}
    if data:
        # Build lookup of part_name -> normalized value entered by user
        for comp in edb.components.components.values():
            key = f"val_{comp.part_name}"
            if key in data and data[key]:
                val = normalize_value(data[key])
                if val and val != str(_get_comp_value(comp)):
                    changes[comp.part_name] = val
        if changes:
            for comp in edb.components.components.values():
                if comp.part_name in changes:
                    _set_comp_value(comp, changes[comp.part_name])
            edb.save()
    edb.close_edb()

    if changes:
        with open(os.path.join(output_dir, "updated_values.json"), "w") as fp:
            json.dump(changes, fp)
    return {}

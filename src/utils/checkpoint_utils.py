from pathlib import Path

import numpy as np
import random, os
import pickle

BACKUP_DIR = Path("../data/ga_checkpoints")

def save_ga_checkpoint(run_tag, state_data, city_name):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}_{run_tag}.pikl"
    temp_filepath = filepath.with_suffix('.pikl.tmp')

    state_data["python_random_state"] = random.getstate()
    state_data["numpy_random_state"] = np.random.get_state()

    with open(temp_filepath, 'wb') as f:
        pickle.dump(state_data, f)

    temp_filepath.replace(filepath)

def load_ga_checkpoint(run_tag, city_name) -> dict:
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}_{run_tag}.pikl"

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except (EOFError, pickle.UnpicklingError):
        print(f"Warning: Checkpoint file is corrupted: {filepath}")
        return None

def delete_ga_checkpoint(run_tag, city_name):
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}_{run_tag}.pikl"
    if filepath.exists():
        filepath.unlink()

def save_data(data, path):
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'wb') as f:
        pickle.dump(data, f)

def load_data(path):
    with open(path, 'rb') as f:
        return pickle.load(f)

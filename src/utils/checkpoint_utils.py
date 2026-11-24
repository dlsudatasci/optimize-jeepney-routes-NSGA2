import pickle
import random
from pathlib import Path

import numpy as np

BACKUP_DIR = Path("../data/ga_checkpoints")

def save_ga_checkpoint(run_tag, state_data, city_name):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}{run_tag}.pkl"
    temp_filepath = filepath.with_suffix('.pkl.tmp')

    state_data["python_random_state"] = random.getstate()
    state_data["numpy_random_state"] = np.random.get_state()

    with open(temp_filepath, 'wb') as f:
        pickle.dump(state_data, f)

    temp_filepath.replace(filepath)

def load_ga_checkpoint(run_tag, city_name) -> dict:
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}_{run_tag}.pkl"

    if not filepath.exists():
        return None

    try:
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    except (EOFError, pickle.UnpicklingError):
        print(f"Warning: Checkpoint file is corrupted: {filepath}")
        return None

def delete_ga_checkpoint(run_tag, city_name):
    filepath = BACKUP_DIR / f"GA_checkpoint_{city_name}_{run_tag}.pkl"
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

def save_final_networks(run_tag: str, networks: list, city_name: str, hv_history: list | None = None):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    filepath = BACKUP_DIR / f"GA_final_{city_name}_{run_tag}.pkl"
    temp_filepath = filepath.with_suffix(".pkl.tmp")

    payload = {
        "best_population": networks,
        "hv_history": hv_history or [],
    }

    with open(temp_filepath, "wb") as f:
        pickle.dump(payload, f)

    temp_filepath.replace(filepath)

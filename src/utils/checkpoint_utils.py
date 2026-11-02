from pathlib import Path

import numpy as np
import random, os
import pickle

def ga_checkpoint_filename(run_tag=""):
    return f"GA Backup Files/GA_checkpoint_Makati{run_tag}.pikl"

def ga_best_population_filename(run_tag=""):
    return f"GA Backup Files/GA_recent_best_population_Makati_backup{run_tag}.pikl"

def save_ga_checkpoint(
    run_tag,
    generation_num,
    network_population,
    max_score_list,
    most_optimal_gen,
    prev_max_fitness_score,
    plateau_counter,
    current_highest_max_score,
    current_highest_avg_score,
    elapsed_seconds,
):
    data = {
        "generation_num": generation_num,
        "population": network_population,
        "max_score_list": max_score_list,
        "most_optimal_gen": most_optimal_gen,
        "prev_max_fitness_score": prev_max_fitness_score,
        "plateau_counter": plateau_counter,
        "current_highest_max_score": current_highest_max_score,
        "current_highest_avg_score": current_highest_avg_score,
        "elapsed_seconds": elapsed_seconds,
        "python_random_state": random.getstate(),
        "numpy_random_state": np.random.get_state(),
    }
    save_data(data, ga_checkpoint_filename(run_tag))

def load_ga_checkpoint(run_tag=""):
    filename = ga_checkpoint_filename(run_tag)
    if not os.path.exists(filename):
        return None
    try:
        return load_data(filename)
    except (EOFError, pickle.UnpicklingError):
        print(f"Warning: checkpoint file is corrupted or incomplete: {filename}")
        return None

def delete_ga_checkpoint(run_tag=""):
    checkpoint_file = ga_checkpoint_filename(run_tag)
    best_population_file = ga_best_population_filename(run_tag)

    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
    if os.path.exists(best_population_file):
        os.remove(best_population_file)

def save_data(data, path):
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Safe atomic save
    temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
    with open(temp_path, 'wb') as f:
        pickle.dump(data, f)
    temp_path.replace(filepath)

def load_data(path):
    with open(path, 'rb') as f:
        return pickle.load(f)

# Export most recent population into pikl in case of errors
def save_recent_population(population_num, population, run_tag=""):
    filename = f"GA Backup Files/GA_recent_population_Makati_backup{run_tag}.pikl"
    data = {
        "population": population,
        "population_num": population_num,
    }

    save_data(data, filename)


# Export current best population into pikl in case of errors
def save_recent_best_population(population_num, population, run_tag=""):
    filename = f"GA Backup Files/GA_recent_best_population_Makati_backup{run_tag}.pikl"
    data = {
        "population": population,
        "population_num": population_num,
    }

    save_data(data, filename)

# Export current best population into pikl in case of errors
def save_max_score_list(population_num, max_list, run_tag=""):
    filename = f"GA Backup Files/GA_max_score_list_Makati_backup{run_tag}.pikl"
    data = {
        "max_list": max_list,
        "population_num": population_num,
    }

    save_data(data, filename)

def _pct_tag(w):
    """
    Convert weight (0.6) -> '60', (0.02) -> '02', (1.0) -> '100'
    Assumes weights are in [0,1].
    """
    return f"{int(round(w * 100)):02d}"  # 0.1->10, 0.05->05

def make_run_tag(weights):
    return (
        f"cov{_pct_tag(weights["w_cov"])}"
        f"_int{_pct_tag(weights["w_int"])}"
        f"_ext{_pct_tag(weights["w_ext"])}"
        f"_vul{_pct_tag(weights["w_vul"])}"
        f"_rob{_pct_tag(weights["w_rob"])}"
    )

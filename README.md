# optimize-jeepney-routes-NSGA2

## Prerequisites
* Python free-threading
* GDAL
* uv package manager

## Setup
Run if u wanna update the venv:
```
uv sync
```
Run if u wanna add a package:
```
uv add <package>
```

Run if u wanna update the amenity map submodule:
```
git submodule update --remote
```

optimize-jeepney-routes-NSGA2/
├── .gitignore
├── .gitmodules
├── README.md
├── pyproject.toml
├── uv.lock
├── download_osm.sh
├── data/
│   ├── amenity_maps/
│   ├── eda/
│   │   ├── eda_design_inputs.csv
│   │   ├── original_network_baseline.csv
│   ├── ga_checkpoints/
│   ├── initial_route_sets/
│   ├── jeepney_routes/
│   ├── population_distribution/
│   ├── saved_networks/
│   ├── street_networks/
├── notebooks/
│   ├── City_Zone_Creation.ipynb
│   ├── EDA.ipynb
│   ├── IRSG.ipynb
│   ├── NSGA-II_Route_Network_Optimization.ipynb
│   ├── Original Jeepney Routes.ipynb
│   ├── Taguig_CZC.ipynb
│   ├── archive/
├── plots/
│   ├── Crossover Result Maps/
│   ├── GA Generation Graphs/
│   ├── GA Result Route Networks HTML/
│   ├── Generated Route Networks HTML/
│   ├── Initial Route Set Maps/
│   ├── Original Jeepney Maps/
│   ├── Population Maps/
│   ├── Result Route Networks/
│   ├── Stop Maps/
│   ├── Zone Creation/
│   ├── eda/
│   ├── transpo_mandaluyong.html
├── src/
│   ├── analysis/
│   │   ├── baseline.py
│   │   ├── build_original.py
│   │   ├── capacity.py
│   │   ├── catchment.py
│   │   ├── descriptive.py
│   │   ├── figures.py
│   │   ├── original_network.py
│   │   ├── overlap.py
│   ├── config/
│   │   ├── config.py
│   ├── genetic_algorithm/
│   │   ├── crossover.py
│   │   ├── fitness.py
│   │   ├── mutate.py
│   │   ├── reverse_routes.py
│   │   ├── schema.py
│   ├── utils/
│   │   ├── checkpoint_utils.py
│   │   ├── graph_utils.py
│   │   ├── make_population_csv.py
│   │   ├── route_utils.py
│   │   ├── time_utils.py
├── tests/
│   ├── conftest.py
│   ├── test_mutate.py


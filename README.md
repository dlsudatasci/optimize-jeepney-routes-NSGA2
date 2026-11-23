# optimize-jeepney-routes-NSGA2

A multi-objective Genetic Algorithm (NSGA-II) for optimizing Metro Manila jeepney transit route networks using OpenStreetMap road graphs.

## Prerequisites
- Python: 3.11+ (Python 3.15t free-threading recommended for true parallelism)
- GDAL
- uv package manager

## Setup
1. Clone the repository and initialize the submodule:
```bash
  git clone https://github.com/dlsudatasci/optimize-jeepney-routes-nsga2.git
  cd optimize-jeepney-routes-nsga2
  git submodule update --init --recursive
```

2. Install dependencies and sync the venv:
```bash
uv sync
# (To add a new package: uv add <package>)
```

3. Download OpenStreetMap street networks (Optional):
```bash
bash download_osm.sh
```

## Project Structure
```bash
optimize-jeepney-routes-NSGA2/
├── download_osm.sh              # Script to fetch OSM street network GraphML files
├── pyproject.toml               # Project dependencies and uv configuration
├── uv.lock                      # Locked dependency versions
├── data/
│   ├── amenity_maps/            # GeoJSON amenity points & polygons per city (git submodule)
│   ├── eda/                     # Baseline network metrics and EDA inputs
│   ├── ga_checkpoints/          # Saved GA state checkpoints (.pkl)
│   ├── initial_route_sets/      # Generated initial populations & stop sets (.pkl)
│   ├── jeepney_routes/          # Existing/baseline jeepney route CSVs
│   ├── population_distribution/ # Population data per city
│   ├── rail_layer/              # Rail station coordinates (rail_stations.json)
│   ├── saved_networks/          # Pickled zone, amenity, stop, and optimized GA networks
│   └── street_networks/         # City road network graphs (.graphml)
├── notebooks/
│   ├── City_Zone_Creation.ipynb # Amenity Zone Creation (used by IRSG)
│   ├── Taguig_CZC.ipynb         # Separate CZC for Taguig City
│   ├── EDA.ipynb
│   ├── IRSG.ipynb               # Initial Route Set Generation
│   ├── NSGA-II_Route_Network_Optimization.ipynb
│   └── archive/                 # Legacy experiment notebooks
├── plots/
│   ├── Crossover Result Maps/   # Parent/child crossover inspection maps
│   ├── EDA/                     # Catchment, overlap, and baseline figures
│   ├── Initial Route Set Maps/  # Baseline IRSG route maps
│   ├── Original Jeepney Maps/   # Existing jeepney route visualizations
│   ├── Population Maps/         # Spatial population heatmaps/choropleths
│   ├── Stop Maps/               # Generated stop location maps
│   └── Zone Creation/           # Intermediate zone merging and filtering maps
├── src/
│   ├── analysis/                # Baseline, capacity, catchment, overlap, and figure scripts
│   ├── config/                  # Hyperparameters, fitness weights, and constants
│   ├── genetic_algorithm/       # NSGA-II operators (crossover, mutate, fitness, reverse_routes, schema)
│   └── utils/                   # Checkpointing, graph helpers, map layers, and timing utilities
└── tests/                       # Unit tests for route mutation
```
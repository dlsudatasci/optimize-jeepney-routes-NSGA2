WALKING_DISTANCES = [300,550,800]
MAX_DISTANCE = 15
CONNECTION_TYPES = ["Default", "Area", "Degree", "Mixed"]

TARGET_NODE_RATIO = 0.75   #for N_i
MIN_INTERSECTIONS_PER_ROUTE = 3   # n for r_i
MIN_TRANSPO_STOPS_PER_ROUTE = 2   # n for r_e

# capex
STOP_COST = 28000
STOP_SIZES = [27.0, 40.5, 54.0]
MAX_DEGREE = [3, 5, 999999]
MAX_BUDGET = 200000000 # placeholder, modify based on city

FITNESS_WEIGHTS = {
    "w_cov": 0.20,
    "w_int": 0.20,
    "w_ext": 0.20,
    "w_vul": 0.20,
    "w_rob": 0.20,
}

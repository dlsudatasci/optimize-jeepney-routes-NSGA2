# IRSG
N_NETWORKS = 100
WALKING_DISTANCES = [500, 750, 1000] # changed to thesis paper
WD_TO_USE = 1
MAX_DISTANCE = 15
N_ROUTES = {"Makati":28, "Manila":50, "Taguig":18, "Mandaluyong":10} # og routes count (manila capped at 50 for runtime concerns)
STOP_MIN = 20

CONNECTION_TYPES = ["Default", "Area", "Degree", "Mixed"]
TARGET_NODE_RATIO = 0.75   #for N_i
MIN_INTERSECTIONS_PER_ROUTE = 3   # n for r_i
MIN_TRANSPO_STOPS_PER_ROUTE = 2   # n for r_e

# capex
STOP_COST = 28000
STOP_SIZES = [27.0, 40.5, 54.0]
MAX_DEGREE = [3, 5, 999999]
MAX_BUDGET = 200000000 # placeholder, modify based on city

# Z_user
#
# Two transfer radii plus the catchment radius. Walking is free in every case:
# the cost of changing is carried entirely by TRANSFER_PENALTY_MIN, which bundles
# the walk with the inconvenience.
#
#   JEEP_TRANSFER_MAX_M    jeep -> jeep. Shorter, because swapping between
#                          jeepney routes is a mid-journey manoeuvre and should
#                          happen where the routes are practically co-located.
#   RAIL_TRANSFER_MAX_M    jeep <-> rail. Longer, because walking to a trunk
#                          station is worth more effort and reaches a faster mode.
#
# Rail -> rail transfers are fixed pairs (RAIL_INTERCHANGES in rail_layer), not
# distance-based: those are purpose-built interchange infrastructure.
JEEP_TRANSFER_MAX_M = 250.0
RAIL_TRANSFER_MAX_M = 500.0
TRANSFER_PENALTY_MIN = 5.0     # minutes of perceived cost per mode/line change
CATCHMENT_RADIUS_M = 500.0     # radius of a stop's population catchment

# Returned when a network cannot be scored (no routes, no OD set, no population
# in any catchment, or nothing reachable). Finite, and small enough not to
# destroy the objective vector if it is ever normalised: Makati measures ~6e9,
# Manila an order of magnitude above, so 1e12 leaves ~3 decades of headroom.
INVALID_NETWORK_COST = 1e12

FITNESS_WEIGHTS = {
    "w_cov": 0.20,
    "w_int": 0.10,
    "w_ext": 0.10,
    "w_vul": 0.20,
    "w_rob": 0.20,
    "w_red": 0.20,
}

FILTER_OPTIONS = ['primary', 'secondary', 'tertiary', 'trunk', 'unclassified']

class Stop:
    def __init__(self, lat: float, long: float, isTranspo: bool, stop_id: int, area):
        self.lat = lat
        self.long = long
        self.isTranspo = isTranspo # if it is an existing transpo amenity
        self.enabled = False
        self.stop_id = stop_id
        self.area = area
        self.degree = 0

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

class Route:
    def __init__(self, route: list[tuple], route_id: str, length: float, line_id: int, direction: str):
        self.route = route
        self.route_id = route_id
        self.length = length
        self.line_id = line_id
        self.direction = direction

class Network:
    def __init__(self, routes: list[Route], stops, graph):
        self.routes = routes
        self.stops = stops
        self.graph = graph
        self.fitness_score = 0
        self.fitness_score_components = {} # Individual components for fitness
        # self.reversed_stops = reversed_stops
        # self.reversed_routes = reversed_routes

class Generation:
    def __init__(self, networks: list[Network], conn_type: str, total_road_distance: float, walking_distance: int):
        self.networks = networks
        self.conn_type = conn_type
        self.total_road_distance = total_road_distance
        self.walking_distance = walking_distance

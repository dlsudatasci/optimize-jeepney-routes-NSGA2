class StopCandidate:
    def __init__(self, lat, long, isTranspo, id, area):
        self.lat = lat
        self.long = long
        self.isTranspo = isTranspo
        self.enabled = False
        self.id = id #Stop ID
        self.area = area
        self.degree = 0

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def getLat(self):
        return self.lat

    def getLong(self):
        return self.long

    def getArea(self):
        return self.area

    def getDegree(self):
        return self.degree

class Generation:
    def __init__(self, networks: list[Network], conn_type: str, total_road_distance, walking_distance):
        self.networks = networks
        self.conn_type = conn_type
        self.total_road_distance = total_road_distance
        self.walking_distance = walking_distance

class Network:
    def __init__(self, routes: list[Route], reversed_routes, stops, reversed_stops, graph):
        self.routes = routes
        self.stops = stops
        self.graph = graph
        self.reversed_routes = reversed_routes
        self.reversed_stops = reversed_stops
        self.fitness_score = 0
        self.fitness_score_components = {} # Individual components for fitness

class Route:
    def __init__(self, route, route_id, length):
        self.route = route
        self.route_id = route_id
        self.length = length

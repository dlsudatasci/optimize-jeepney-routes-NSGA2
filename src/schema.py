class stopCandidate:
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
    def __init__(self, networks, conn_type, total_road_distance, walking_distance):
        self.networks = networks
        self.conn_type = conn_type
        self.total_road_distance = total_road_distance
        self.walking_distance = walking_distance

class Network:
    def __init__(self, routes, reversed_routes, stops, reversed_stops, graph, walk_distance, total_road_distance):
        self.routes = routes
        self.reversed_routes = reversed_routes
        self.stops = stops
        self.reversed_stops = reversed_stops
        self.fitness_score = 0
        self.graph = graph
        self.walk_distance = walk_distance
        self.total_road_distance = total_road_distance
        self.fitness_score_components = {}

class Route:
    def __init__(self, route, route_id, length):
        self.route = route
        self.route_id = route_id
        self.length = length

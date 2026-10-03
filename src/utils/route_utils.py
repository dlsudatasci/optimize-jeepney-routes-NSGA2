def add_stops_to_list(routes):
    used_stops = []
    for route in routes:
        if route is None:
            continue

        for conn in route.route:
            if conn[0] not in used_stops:
                used_stops.append(conn[0])
            if conn[-1] not in used_stops:
                used_stops.append(conn[-1])
    return used_stops

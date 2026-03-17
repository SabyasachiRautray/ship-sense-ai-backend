import requests
from config import ORS_API_KEY


CITY_COORDS = {
    "Mumbai":    [72.8777, 19.0760],
    "Delhi":     [77.1025, 28.7041],
    "Bangalore": [77.5946, 12.9716],
    "Chennai":   [80.2707, 13.0827],
    "Kolkata":   [88.3639, 22.5726],
    "Pune":      [73.8567, 18.5204],
    "Hyderabad": [78.4867, 17.3850],
    "Ahmedabad": [72.5714, 23.0225],
    "Jaipur":    [75.7873, 26.9124],
    "Surat":     [72.8311, 21.1702],
}

# Flight routes with avg duration in hours
AIR_ROUTES = {
    ("Mumbai", "Delhi"):      {"via": "BOM→DEL", "hours": 2.1},
    ("Delhi", "Mumbai"):      {"via": "DEL→BOM", "hours": 2.1},
    ("Mumbai", "Bangalore"):  {"via": "BOM→BLR", "hours": 1.5},
    ("Bangalore", "Mumbai"):  {"via": "BLR→BOM", "hours": 1.5},
    ("Chennai", "Delhi"):     {"via": "MAA→DEL", "hours": 2.5},
    ("Delhi", "Chennai"):     {"via": "DEL→MAA", "hours": 2.5},
    ("Kolkata", "Delhi"):     {"via": "CCU→DEL", "hours": 2.0},
    ("Delhi", "Kolkata"):     {"via": "DEL→CCU", "hours": 2.0},
    ("Mumbai", "Kolkata"):    {"via": "BOM→CCU", "hours": 2.3},
    ("Kolkata", "Mumbai"):    {"via": "CCU→BOM", "hours": 2.3},
    ("Hyderabad", "Mumbai"):  {"via": "HYD→BOM", "hours": 1.4},
    ("Mumbai", "Hyderabad"):  {"via": "BOM→HYD", "hours": 1.4},
    ("Chennai", "Kolkata"):   {"via": "MAA→CCU", "hours": 2.0},
    ("Kolkata", "Chennai"):   {"via": "CCU→MAA", "hours": 2.0},
    ("Bangalore", "Delhi"):   {"via": "BLR→DEL", "hours": 2.7},
    ("Delhi", "Bangalore"):   {"via": "DEL→BLR", "hours": 2.7},
    ("Hyderabad", "Delhi"):   {"via": "HYD→DEL", "hours": 2.2},
    ("Delhi", "Hyderabad"):   {"via": "DEL→HYD", "hours": 2.2},
    ("Chennai", "Mumbai"):    {"via": "MAA→BOM", "hours": 1.8},
    ("Mumbai", "Chennai"):    {"via": "BOM→MAA", "hours": 1.8},
}

# Waterway routes between coastal/river cities
WATER_ROUTES = {
    ("Mumbai", "Surat"):    {"via": "Arabian Sea coast",  "hours": 8.0,  "km": 280},
    ("Surat", "Mumbai"):    {"via": "Arabian Sea coast",  "hours": 8.0,  "km": 280},
    ("Mumbai", "Kolkata"):  {"via": "Coastal sea route",  "hours": 72.0, "km": 2100},
    ("Kolkata", "Mumbai"):  {"via": "Coastal sea route",  "hours": 72.0, "km": 2100},
    ("Chennai", "Kolkata"): {"via": "Bay of Bengal",      "hours": 48.0, "km": 1400},
    ("Kolkata", "Chennai"): {"via": "Bay of Bengal",      "hours": 48.0, "km": 1400},
    ("Mumbai", "Chennai"):  {"via": "Arabian Sea → tip",  "hours": 40.0, "km": 1200},
    ("Chennai", "Mumbai"):  {"via": "Coastal sea route",  "hours": 40.0, "km": 1200},
}

# Alternate road waypoints to bypass congested corridors
ALTERNATE_ROADS = {
    ("Mumbai", "Delhi"):    {"via": "Surat→Ahmedabad→Jaipur",     "extra_km": 80},
    ("Delhi", "Mumbai"):    {"via": "Jaipur→Ahmedabad→Surat",     "extra_km": 80},
    ("Mumbai", "Kolkata"):  {"via": "Nagpur→Raipur→Kolkata",      "extra_km": 50},
    ("Chennai", "Delhi"):   {"via": "Hyderabad→Nagpur→Bhopal",    "extra_km": 70},
    ("Bangalore", "Delhi"): {"via": "Pune→Nashik→Indore→Agra",    "extra_km": 90},
    ("Delhi", "Kolkata"):   {"via": "Agra→Varanasi→Kolkata",      "extra_km": 60},
    ("Mumbai", "Chennai"):  {"via": "Pune→Hyderabad→Chennai",     "extra_km": 45},
}


#  Road 

def _get_road(origin: str, destination: str) -> dict:
    try:
        oc = CITY_COORDS.get(origin)
        dc = CITY_COORDS.get(destination)

        if not oc or not dc:
            return _road_fallback(origin, destination, "City not in map")

        url     = "https://api.openrouteservice.org/v2/directions/driving-car"
        headers = {"Authorization": ORS_API_KEY}
        res     = requests.post(url, json={"coordinates": [oc, dc]}, headers=headers, timeout=8)
        data    = res.json()

        seg          = data["routes"][0]["segments"][0]
        duration_hrs = round(seg["duration"] / 3600, 2)
        distance_km  = round(seg["distance"] / 1000, 1)
        base         = distance_km / 60
        delay        = round(max(duration_hrs - base, 0), 2)
        congestion   = "High" if delay > 2 else "Medium" if delay > 0.5 else "Low"

        # Build alternate route suggestion if there's delay
        alt = None
        if delay > 0.5:
            alt_info = ALTERNATE_ROADS.get((origin, destination))
            if alt_info:
                alt_dist = distance_km + alt_info["extra_km"]
                alt_hrs  = round(alt_dist / 65, 2)
                alt = {
                    "via":              alt_info["via"],
                    "distance_km":      alt_dist,
                    "duration_hours":   alt_hrs,
                    "time_saved_hours": round(max(duration_hrs - alt_hrs, 0), 2),
                    "recommended":      alt_hrs < duration_hrs
                }

        return {
            "mode":                  "road",
            "distance_km":           distance_km,
            "duration_hours":        duration_hrs,
            "estimated_delay_hours": delay,
            "congestion_level":      congestion,
            "alternate_route":       alt,
        }

    except Exception as e:
        return _road_fallback(origin, destination, str(e))


def _road_fallback(origin: str, destination: str, error: str = "") -> dict:
    return {
        "mode":                  "road",
        "distance_km":           500,
        "duration_hours":        9.0,
        "estimated_delay_hours": 1.5,
        "congestion_level":      "Medium",
        "alternate_route":       None,
        "note":                  f"Fallback data. {error}".strip()
    }


#  Air 

def _get_air(origin: str, destination: str) -> dict:
    route = AIR_ROUTES.get((origin, destination))
    if not route:
        return {"mode": "air", "available": False, "reason": "No direct air route found"}

    return {
        "mode":                  "air",
        "available":             True,
        "via":                   route["via"],
        "duration_hours":        route["hours"],
        "estimated_delay_hours": 0.5,        # avg airport processing buffer
        "congestion_level":      "Low",
        "note":                  "Includes 30min airport delay buffer"
    }


# Water

def _get_water(origin: str, destination: str) -> dict:
    route = WATER_ROUTES.get((origin, destination))
    if not route:
        return {"mode": "water", "available": False, "reason": "No waterway route found"}

    return {
        "mode":                  "water",
        "available":             True,
        "via":                   route["via"],
        "distance_km":           route["km"],
        "duration_hours":        route["hours"],
        "estimated_delay_hours": round(route["hours"] * 0.1, 1),  
        "congestion_level":      "Low",
        "note":                  "Best for bulk/heavy cargo only"
    }


# Main entry point 

def get_traffic(origin: str, destination: str) -> dict:
    road  = _get_road(origin, destination)
    air   = _get_air(origin, destination)
    water = _get_water(origin, destination)

    # Find fastest available mode
    options = [{"mode": "road", "hours": road.get("duration_hours", 99)}]
    if air.get("available"):
        options.append({"mode": "air",   "hours": air.get("duration_hours", 99)})
    if water.get("available"):
        options.append({"mode": "water", "hours": water.get("duration_hours", 99)})

    fastest = min(options, key=lambda x: x["hours"])

    return {
        "road":           road,
        "air":            air,
        "water":          water,
        "fastest_mode":   fastest["mode"],
        "fastest_hours":  fastest["hours"],
        "recommendation": f"Use {fastest['mode']} — fastest at {fastest['hours']} hours"
    }
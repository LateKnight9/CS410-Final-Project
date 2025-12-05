# app/optimization_engine.py

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict
from .data_models import ItineraryRequest 
import math 

def create_time_matrix(locations: List[Tuple[float, float]], travel_speed_kmph: float = 20) -> np.ndarray:
    """
    Calculates travel time between all pairs of locations using Haversine distance.
    (Placeholder for simplicity; real projects require a Map API for accuracy.)
    """
    num_locations = len(locations)
    time_matrix = np.zeros((num_locations, num_locations), dtype=int)
    
    R = 6371 # Earth radius in km
    
    def haversine(lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        distance_km = R * c
        return distance_km

    for i in range(num_locations):
        for j in range(num_locations):
            if i != j:
                lat1, lon1 = locations[i]
                lat2, lon2 = locations[j]
                distance_km = haversine(lat1, lon1, lat2, lon2)
                # Time in minutes = (Distance / Speed) * 60
                time_minutes = int((distance_km / travel_speed_kmph) * 60)
                time_matrix[i, j] = time_minutes
    return time_matrix.tolist()

def solve_vrptw_for_day(attractions_df: pd.DataFrame, daily_request: ItineraryRequest) -> List[Dict]:
    """
    Solves the Vehicle Routing Problem with Time Windows (VRPTW) 
    to create an optimized daily itinerary.
    """
    # 1. Prepare Locations and Data Model
    locations = [(r.latitude, r.longitude) for r in attractions_df.itertuples()]
    
    if not locations:
        return [{"error": "No attractions found for the given criteria."}]
        
    # Add a virtual depot/starting point (Index 0)
    DEPOT_LOCATION = (locations[0][0], locations[0][1])
    full_locations = [DEPOT_LOCATION] + locations
    
    data = {}
    data['time_matrix'] = create_time_matrix(full_locations)
    data['num_locations'] = len(full_locations)
    data['num_vehicles'] = 1 
    data['depot'] = 0 
    
    # Time Windows for each location (in minutes from midnight)
    
    # --- ROBUST TIME WINDOW FIX: Ensure Integer Safety and Check Constraints ---
    daily_start = daily_request.daily_start_hour * 60
    daily_end = daily_request.daily_end_hour * 60
    time_windows = [(daily_start, daily_end)] # Time window for the depot/vehicle (Index 0)

    for r in attractions_df.itertuples():
        # 1. Handle Invalid Data (NaNs/Non-numeric)
        try:
            # Safely cast all required values to integers (minutes from midnight)
            # Use math.isnan check as an alternative to handle NumPy NaNs explicitly if needed, 
            # though the try/except block generally catches them upon int() conversion.
            if math.isnan(r.open_time) or math.isnan(r.close_time) or math.isnan(r.avg_visit_duration):
                 raise ValueError("NaN detected in time data")
                 
            open_time = int(r.open_time)
            close_time = int(r.close_time)
            visit_duration = int(r.avg_visit_duration)
        except (ValueError, TypeError):
            # If any value is NaN or otherwise invalid, set a full-day range as a fallback
            print(f"Warning: Attraction '{r.name}' has invalid time data. Setting full-day range.")
            time_windows.append((daily_start, daily_end))
            continue # Skip to the next attraction
            
        # 2. Calculate Constrained Time Window
        start = open_time # Earliest start time is opening time
        # Latest possible visit START time = Closing Time - Visit Duration
        end = close_time - visit_duration 
        
        # 3. Check for Impossible Constraint
        if end < start:
             # If the required visit duration is longer than the open hours
             print(f"Warning: Attraction '{r.name}' is impossible to schedule (Duration > Open Hours). Setting full-day range.")
             time_windows.append((daily_start, daily_end))
        else:
             # Set the valid, constrained window for the visit START time
             time_windows.append((start, end)) 
             
    data['time_windows'] = time_windows
    # --------------------------------------------------------------------------


    # 2. Setup OR-Tools
    manager = pywrapcp.RoutingIndexManager(data['num_locations'], data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    # 3. Time Callback and Cost Definition
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        
        # Add the fixed visit duration ONLY if the 'from' node is an attraction (not the depot)
        duration = 0
        if from_node > 0: 
             # The attraction data corresponds to index - 1 because of the depot offset
             duration = attractions_df.iloc[from_node - 1]['avg_visit_duration']
             
        # Total cost is Travel Time + Visit Duration
        return data['time_matrix'][from_node][to_node] + duration

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 4. Add Time Dimension (The core constraint for Time Windows)
    time = 'Time'
    # Set maximum time to the end of the travel day
    routing.AddDimension(
        transit_callback_index,
        0, # Slack (max waiting time allowed at a node)
        daily_end, # Max total time (end of day)
        True, # Force start cumul to zero
        time)
    time_dimension = routing.GetDimensionOrDie(time)

    # Add Time Window Constraints for all locations
    for location_idx, time_window in enumerate(data['time_windows']):
        index = manager.NodeToIndex(location_idx)
        # This line is where the constraint is set.
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # 5. Search Parameters and Solve
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 5 # Set a time limit for the solver

    solution = routing.SolveWithParameters(search_parameters)
    
    # 6. Interpret Solution
    if not solution:
        # If the solver fails, return the specific error message
        return [{"error": "Optimization failed to find a feasible route. Try reducing the number of stops or increasing the daily available time."}]

    def get_route(solution, routing, manager):
        route = []
        index = routing.Start(0)
        time_dimension = routing.GetDimensionOrDie('Time')
        
        # Traverse the solution path
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            
            # Skip the depot (node index 0)
            if node_index > 0:
                # Retrieve data for the scheduled attraction
                attr_data = attractions_df.iloc[node_index - 1].to_dict()
                time_var = time_dimension.CumulVar(index)
                
                # The cumulative variable is the start time of the activity at this node.
                start_time_minutes = solution.Min(time_var)
                end_time_minutes = start_time_minutes + attr_data['avg_visit_duration']
                
                route.append({
                    "attraction_name": attr_data['name'],
                    "start_time_minutes": int(start_time_minutes),
                    "end_time_minutes": int(end_time_minutes),
                    "arrival_time": f"{int(start_time_minutes) // 60:02d}:{int(start_time_minutes) % 60:02d}:00",
                })
            index = solution.Value(routing.NextVar(index))
            
        return route

    return get_route(solution, routing, manager)

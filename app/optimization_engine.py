# app/optimization_engine.py

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import pandas as pd
import numpy as np
from typing import List, Tuple, Dict # Imported for type hinting
from .data_models import ItineraryRequest # Assuming ItineraryRequest is accessible

def create_time_matrix(locations: List[Tuple[float, float]], travel_speed_kmph: float = 20) -> np.ndarray:
    """
    Calculates travel time between all pairs of locations using Haversine distance.
    (NOTE: This is a placeholder; real projects require a Map API for accurate travel time.)
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
    # Add a virtual depot/starting point (Index 0)
    DEPOT_LOCATION = (locations[0][0], locations[0][1]) # Assuming first location is start/end
    full_locations = [DEPOT_LOCATION] + locations
    
    data = {}
    data['time_matrix'] = create_time_matrix(full_locations)
    data['num_locations'] = len(full_locations)
    data['num_vehicles'] = 1 
    data['depot'] = 0 
    
    # Time Windows for each location (in minutes from midnight)
    time_windows = [(daily_request.daily_start_hour * 60, daily_request.daily_end_hour * 60)] # Depot/Day window

    # --- CRITICAL FIX APPLIED HERE ---
    for r in attractions_df.itertuples():
        start = r.open_time
        # Max start time must ensure the visit (r.avg_visit_duration) ends before closing (r.close_time).
        end = r.close_time - r.avg_visit_duration
        
        # Guardrail against impossible scheduling (e.g., duration > open hours)
        if end < start:
             # If impossible, set the window to the smallest possible valid range 
             # (or skip/filter this attraction upstream for robustness).
             # We set a large range to allow the solver to "skip" it implicitly if possible.
             # Alternatively, let's make it explicitly impossible if end < start:
             time_windows.append((start, start - 1)) # Impossible range (min > max)
        else:
             # The solver seeks to find a visit START time between 'start' and 'end'
             time_windows.append((start, end)) 
             
    data['time_windows'] = time_windows

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
        daily_request.daily_end_hour * 60, # Max total time (end of day)
        True, # Force start cumul to zero
        time)
    time_dimension = routing.GetDimensionOrDie(time)

    # Add Time Window Constraints for all locations
    # Line 97 from the original traceback is here. It uses the corrected time_windows list.
    for location_idx, time_window in enumerate(data['time_windows']):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # 5. Search Parameters and Solve
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_parameters)
    
    # 6. Interpret Solution
    if not solution:
        # If the solver fails, return the specific error message
        return [{"error": "Optimization failed to find a feasible route. Check time windows and travel times."}]

    def get_route(solution, routing, manager):
        route = []
        index = routing.Start(0)
        time_dimension = routing.GetDimensionOrDie('Time')
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            
            # Skip the depot (node index 0)
            if node_index > 0:
                # Retrieve data for the scheduled attraction
                attr_data = attractions_df.iloc[node_index - 1].to_dict()
                time_var = time_dimension.CumulVar(index)
                
                start_time_minutes = solution.Min(time_var)
                end_time_minutes = start_time_minutes + attr_data['avg_visit_duration']
                
                route.append({
                    "attraction_name": attr_data['name'],
                    "start_time_minutes": start_time_minutes,
                    "end_time_minutes": end_time_minutes,
                    "arrival_time": f"{start_time_minutes // 60:02d}:{start_time_minutes % 60:02d}",
                })
            index = solution.Value(routing.NextVar(index))
            
        return route

    return get_route(solution, routing, manager)

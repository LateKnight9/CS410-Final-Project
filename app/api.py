# app/api.py
from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .data_models import ItineraryRequest, Attraction
from .nlp_processor import apply_sentiment_and_topics
from .recommendation_engine import generate_recommendations
from .optimization_engine import solve_vrptw_for_day

app = Flask(__name__)

# Data Loading and Pre-Processing (Simulates Database/Data Pipeline)
try:
    # Load previously scraped and processed data
    DATA_PATH = 'data/processed_attractions.csv'
    ATTRACTIONS_DATA = pd.read_csv(DATA_PATH)
    # Ensure data is processed 
    ATTRACTIONS_DATA = apply_sentiment_and_topics(ATTRACTIONS_DATA)
except FileNotFoundError:
    print(f"Warning: {DATA_PATH} not found. Creating mock data.")
    #  data for testing the API logic
    ATTRACTIONS_DATA = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Museum A', 'Park B', 'Restaurant C', 'Landmark D', 'Gallery E'],
        'latitude': [40.71, 40.72, 40.73, 40.74, 40.75],
        'longitude': [-74.00, -74.01, -74.02, -74.03, -74.04],
        'rating': [4.8, 4.2, 4.5, 4.9, 3.9],
        'review_count': [1200, 300, 800, 5000, 150],
        'open_time': [540, 480, 720, 600, 570],   # 9am, 8am, 12pm, 10am, 9:30am
        'close_time': [1020, 1320, 1380, 1200, 960], # 5pm, 10pm, 11pm, 8pm, 4pm
        'avg_visit_duration': [120, 180, 90, 60, 150],
        'price_level': [2, 1, 3, 1, 3],
        'themes': ['historical,culture', 'outdoor,adventure', 'food,dining', 'historical,landmark', 'culture,art'],
        'raw_reviews': ['great museum a must see', 'beautiful park excellent trails', 'amazing food very expensive', 'iconic landmark worth the visit', 'nice art but small and dated'],
    })
    ATTRACTIONS_DATA = apply_sentiment_and_topics(ATTRACTIONS_DATA)
    # data so nlp_processor doesn't run every time
    ATTRACTIONS_DATA.to_csv(DATA_PATH, index=False)


@app.route('/generate_itinerary', methods=['POST'])
def generate_itinerary():
    try:
        data = request.get_json()
        req = ItineraryRequest(**data)
    except Exception as e:
        return jsonify({"error": f"Invalid input data: {e}"}), 400

    # 1. Recommendation: Filter and Rank Attractions
    recommended_attractions_df = generate_recommendations(ATTRACTIONS_DATA.copy(), req)
    
    # Take the top N (e.g., 10) most relevant attractions for the trip duration
    trip_duration_days = (datetime.strptime(req.end_date, '%Y-%m-%d') - datetime.strptime(req.start_date, '%Y-%m-%d')).days + 1
    attractions_per_day = 4 # Target activities per day
    max_attractions = min(len(recommended_attractions_df), trip_duration_days * attractions_per_day)

    # --- Daily Itinerary Generation Loop ---
    final_itinerary = []
    current_attraction_pool = recommended_attractions_df.head(max_attractions).copy()
    
    start_date = datetime.strptime(req.start_date, '%Y-%m-%d')

    for day in range(trip_duration_days):
        current_day = start_date + timedelta(days=day)
        
        # Select attractions for the current day's optimization pool
        # Simple selection: take a few from the top of the remaining pool
        daily_pool = current_attraction_pool.head(attractions_per_day).copy()
        
        if daily_pool.empty:
            break

        # 2. Optimization: Solve the Daily TSP with Time Windows
        print(f"DEBUG: Daily Pool for {current_day}:")
        print(daily_pool[['name', 'open_time', 'close_time', 'avg_visit_duration']])
        
        if daily_pool.empty:
             print("DEBUG: daily_pool is empty. Breaking loop.")
             break
        
        daily_route = solve_vrptw_for_day(daily_pool, req)

        # 3. Format Output and Update Pool
        if "error" not in daily_route[0]:
            final_itinerary.append({
                "day": current_day.strftime('%Y-%m-%d'),
                "plan": daily_route
            })
            
            # Remove scheduled items from the overall pool for the next day
            scheduled_names = [item['attraction_name'] for item in daily_route]
            current_attraction_pool = current_attraction_pool[
                ~current_attraction_pool['name'].isin(scheduled_names)]
        else:
             final_itinerary.append({
                "day": current_day.strftime('%Y-%m-%d'),
                "plan": [{"note": daily_route[0]['error']}]
            })
            
    return jsonify({"itinerary": final_itinerary})

# app/recommendation_engine.py
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

def generate_recommendations(attractions_df: pd.DataFrame, request: 'ItineraryRequest') -> pd.DataFrame:
    """Filters and ranks attractions based on user request and attraction data."""
    
    # --- 1. Create User Profile Vector (based on preferences) ---
    # Create a dummy "preference document" by joining user preferences
    user_themes = " ".join(request.preferences)
    
    # --- 2. Create Content Matrix ---
    # Use CountVectorizer on the combined themes/features of attractions
    attraction_features = attractions_df['themes'] + " " + attractions_df['dominant_theme']
    
    # Combine attraction features with user profile into a single series for vectorization
    content_series = pd.concat([pd.Series([user_themes]), attraction_features])
    
    cv = CountVectorizer()
    count_matrix = cv.fit_transform(content_series)
    
    # --- 3. Calculate Similarity (Cosine) ---
    # Calculate cosine similarity between the user vector (row 0) and all attractions (rows 1+)
    cosine_sim = cosine_similarity(count_matrix[0], count_matrix[1:])
    
    # Get scores and map them back to the DataFrame
    attractions_df['similarity_score'] = cosine_sim[0]

    # --- 4. Rank and Filter ---
    
    # Apply a budget filter
    attractions_df = attractions_df[attractions_df['price_level'] <= request.budget]

    # Rank by a composite score: Similarity * (1 + Sentiment) * Rating
    attractions_df['composite_score'] = (
        attractions_df['similarity_score'] * (1 + attractions_df['sentiment_score']) * (attractions_df['rating'] / 5.0) # Normalize rating
    )
    
    return attractions_df.sort_values(by='composite_score', ascending=False)

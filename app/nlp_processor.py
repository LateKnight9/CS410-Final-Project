# app/nlp_processor.py

import pandas as pd
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from typing import List, Dict

def apply_sentiment_and_topics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes raw review text to add sentiment score and topic themes.

    Args:
        df (pd.DataFrame): DataFrame containing an 'raw_reviews' column.

    Returns:
        pd.DataFrame: The input DataFrame augmented with 'sentiment_score' and 
                      'dominant_theme' columns.
    """
    # Ensure pandas is imported at the top, though usually it is passed correctly.
    
    # --- 1. Data Preparation and Cleaning ---
    # Handle NaN values by converting them to an empty string to prevent NLP errors
    df['raw_reviews'] = df['raw_reviews'].fillna('')
    
    # --- 2. Sentiment Analysis (TextBlob) ---
    # Returns the polarity score (-1.0 to 1.0) of the text.
    df['sentiment_score'] = df['raw_reviews'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)

    # --- 3. Topic Modeling (LDA) ---
    
    # Initialize the TF-IDF Vectorizer
    vectorizer = TfidfVectorizer(
        stop_words='english', 
        max_df=0.85, 
        min_df=2, # Ignore terms that appear in too few documents
        max_features=1000 # Limit to the top 1000 features
    )
    
    # Fit and transform the reviews
    tfidf = vectorizer.fit_transform(df['raw_reviews'])
    
    # Define a number of topics
    N_TOPICS = 5
    lda = LatentDirichletAllocation(
        n_components=N_TOPICS, 
        max_iter=5, # Keep low for fast testing; increase for better results
        learning_method='online', 
        random_state=42
    )
    
    # Fit LDA model and transform the data to get topic distribution
    lda.fit(tfidf)
    topic_results = lda.transform(tfidf)
    
    # Get the index of the dominant topic for each attraction
    dominant_topic_indices = topic_results.argmax(axis=1)

    # Convert the NumPy array into a **Pandas Series** before mapping (Fix for AttributeError)
    dominant_topic_series = pd.Series(dominant_topic_indices)

    # Simple function to map index to a thematic label (Customize these labels for your data!)
    topic_labels: Dict[int, str] = {
        0: 'Historical/Museums', 
        1: 'Food/Dining', 
        2: 'Outdoor/Nature',
        3: 'Nightlife/Entertainment',
        4: 'Shopping/Markets'
    }
    
    # Apply the map to assign the thematic label
    df['dominant_theme'] = dominant_topic_series.map(topic_labels)
    
    return df

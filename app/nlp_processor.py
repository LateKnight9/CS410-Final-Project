# app/nlp_processor.py
import pandas as pd
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

def apply_sentiment_and_topics(df: pd.DataFrame) -> pd.DataFrame:
    """Processes raw review text to add sentiment score and topic themes."""
    
    # --- 1. Sentiment Analysis (TextBlob) ---
    df['sentiment_score'] = df['raw_reviews'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)

    # --- 2. Topic Modeling (LDA) ---
    vectorizer = TfidfVectorizer(stop_words='english', max_df=0.85)
    tfidf = vectorizer.fit_transform(df['raw_reviews'])
    
    # Define a number of topics (e.g., 5-10)
    N_TOPICS = 5
    lda = LatentDirichletAllocation(n_components=N_TOPICS, random_state=42)
    lda.fit(tfidf)
    
    # Get the dominant topic index for each attraction
    topic_results = lda.transform(tfidf)
    dominant_topic_indices = topic_results.argmax(axis=1)

    # Simple function to map index to a thematic label (must be refined manually)
    topic_labels = {
        0: 'Historical/Museums', 
        1: 'Food/Dining', 
        2: 'Outdoor/Nature',
        3: 'Nightlife/Entertainment',
        4: 'Shopping/Markets'
    }
    df['dominant_theme'] = dominant_topic_indices.map(topic_labels)
    
    return df

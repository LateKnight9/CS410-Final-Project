# data_ingestion/items.py
import scrapy

class AttractionItem(scrapy.Item):
    """
    Defines the fields for our scraped travel attraction data.
    """
    name = scrapy.Field()             # Attraction Name
    url = scrapy.Field()              # URL to the detailed page
    rating = scrapy.Field()           # Star rating (e.g., 4.5)
    review_count = scrapy.Field()     # Number of reviews
    address = scrapy.Field()          # Full address string
    raw_reviews = scrapy.Field()      # Raw text of reviews (for NLP)
    open_hours_text = scrapy.Field()  # Unstructured text for open hours
    latitude = scrapy.Field()         # Geo-coordinate 
    longitude = scrapy.Field()        # Geo-coordinate

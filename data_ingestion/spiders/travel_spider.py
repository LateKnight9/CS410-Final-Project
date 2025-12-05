# data_ingestion/spiders/travel_spider.py
import scrapy
import pandas as pd
from data_ingestion.items import AttractionItem # Assume this Scrapy Item is defined

class TravelSpider(scrapy.Spider):
    name = 'attraction_crawler'
    allowed_domains = ['example-travel-site.com'] # CHANGE THIS
    start_urls = ['http://example-travel-site.com/attractions'] # CHANGE THIS

    def parse(self, response):
        # Example of locating attraction cards/listings on a results page
        for attraction in response.css('.attraction-card'):
            item = AttractionItem()
            item['name'] = attraction.css('.name::text').get()
            item['rating'] = attraction.css('.rating-value::text').get()
            # ... scrape other fields (hours, duration, reviews URL)
            item['url'] = response.urljoin(attraction.css('a::attr(href)').get())
            yield scrapy.Request(item['url'], callback=self.parse_details, meta={'item': item})
        
        # Follow pagination links
        next_page = response.css('a.next-page::attr(href)').get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)

    def parse_details(self, response):
        # Logic to scrape detailed page for coordinates, full reviews, etc.
        item = response.meta['item']
        
        # Placeholder for extracting reviews text
        full_reviews_text = " ".join(response.css('.review-text::text').getall())
        item['raw_reviews'] = full_reviews_text
        
        # Placeholder for geo-coordinates
        # NOTE: Real-world scraping here often requires external tools or map APIs
        item['latitude'] = 40.7128 # Example: NYC
        item['longitude'] = -74.0060
        
        # Yields the item to the Scrapy pipeline for processing/storage
        yield item

# NOTE: You'd also need to configure a pipeline to save the data to data/processed_attractions.csv

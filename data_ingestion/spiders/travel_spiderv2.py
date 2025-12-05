# data_ingestion/spiders/travel_spider.py
import scrapy
from ..items import AttractionItem # Adjust import based on your exact file structure
import csv # Used for data saving logic

class TravelSpider(scrapy.Spider):
    name = 'attraction_crawler'
    allowed_domains = ['toscrape.com']
    start_urls = ['https://quotes.toscrape.com/'] # Simulates the main listings page
    
    # Simple data list to simulate a pipeline saving to CSV
    # NOTE: In a professional setup, you'd use a proper Scrapy Item Pipeline
    scraped_data = []

    def parse(self, response):
        """
        Parses the listing page (e.g., TripAdvisor results page).
        """
        # We simulate scraping a list of "attractions" (which are 'quotes' here)
        for listing in response.css('div.quote'):
            item = AttractionItem()
            
            # --- 1. Extract High-Level Listing Data ---
            # Simulate extracting name from the author tag
            item['name'] = listing.css('small.author::text').get()
            
            # Simulate using the 'tag' link as the detail page URL
            # The 'toscrape.com/tag/...' link is followed for details
            detail_url = listing.css('div.tags a.tag::attr(href)').get()
            if detail_url:
                item['url'] = response.urljoin(detail_url)
            
            # Placeholder for data we can't extract from this mock site
            item['rating'] = 4.5 
            item['review_count'] = 100
            
            # Yield a request to visit the detail page to collect more info
            yield scrapy.Request(item['url'], callback=self.parse_details, meta={'item': item})
        
        # --- 2. Follow Pagination ---
        next_page = response.css('li.next a::attr(href)').get()
        if next_page is not None:
            yield response.follow(next_page, callback=self.parse)


    def parse_details(self, response):
        """
        Parses the detailed page (e.g., the specific attraction page).
        """
        item = response.meta['item']
        
        # --- 3. Extract Detail Page Data ---
        
        # Simulate collecting the raw review text from the main body
        # In the mock site, we use the quote itself for simulation
        raw_text_parts = response.css('span.text::text').getall()
        item['raw_reviews'] = " ".join(raw_text_parts)
        
        # In a real scenario, you'd use selectors like:
        # item['address'] = response.css('.address-box::text').get()
        # item['open_hours_text'] = response.css('.hours-table span::text').get()
        
        # --- 4. Mock/Placeholder Geo and Address Data ---
        # NOTE: A real project needs a separate step or API call to get these accurately
        item['address'] = "Simulated Location Address"
        item['open_hours_text'] = "Mon-Fri: 9am-5pm"
        # We assign a simple, slightly varied mock coordinate for the optimization engine
        item['latitude'] = 40.7128 + hash(item['name']) % 100 / 1000.0
        item['longitude'] = -74.0060 + hash(item['name']) % 100 / 1000.0
        
        # --- 5. Final Item Yield ---
        self.scraped_data.append(dict(item))
        yield item
        
    def closed(self, reason):
        """
        Called when the spider finishes. Saves the aggregated data to a CSV.
        This replaces the need for a complex Scrapy pipeline in this simple example.
        """
        if self.scraped_data:
            # Convert the list of dicts to a Pandas DataFrame for easy saving
            import pandas as pd
            df = pd.DataFrame(self.scraped_data)
            
            # Save the final data to the location expected by the API
            output_path = 'data/processed_attractions.csv'
            df.to_csv(output_path, index=False)
            print(f"\n✨ Successfully scraped {len(df)} items and saved to {output_path}")

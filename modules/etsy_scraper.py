import requests
import pandas as pd
from datetime import datetime

API_KEY = "g20mj9yn0wiqtxsapkzhsf4u"

def scrape_etsy():
    print("Scraping Etsy via API...")
    
    url = "https://openapi.etsy.com/v3/application/listings/active"
    headers = {"x-api-key": API_KEY}
    params = {
        "keywords": "kashmiri pashmina shawl",
        "limit": 100
    }
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(response.json())

if __name__ == "__main__":
    scrape_etsy()
"""
Weekly auto-update pipeline:
  1. Scrape all 13 competitor sites (with full anti-detection stack)
  2. Compare with existing dataset to find new products
  3. Append new products and save updated CSVs
  4. Log everything to logs/update_log.txt
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from scraper import scrape_all

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(ROOT, 'data')
LOGS_DIR  = os.path.join(ROOT, 'logs')
COMP_CSV  = os.path.join(DATA_DIR, 'competitor_products.csv')
MASTER_CSV = os.path.join(DATA_DIR, 'master_dataset.csv')
LOG_FILE  = os.path.join(LOGS_DIR, 'update_log.txt')

os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(message)s',
    datefmt='%Y-%m-%d %H:%M',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


def run():
    log.info("=" * 60)
    log.info("Weekly auto-update started")

    # 1. scrape
    log.info("Scraping all 13 competitor sites...")
    fresh_df = scrape_all()
    log.info(f"Scraped {len(fresh_df)} shawl products")

    # 2. load existing
    if os.path.exists(COMP_CSV):
        existing      = pd.read_csv(COMP_CSV)
        existing_keys = set(zip(existing['title'], existing['source']))
    else:
        existing      = pd.DataFrame()
        existing_keys = set()

    # 3. find new products
    fresh_df['_key']  = list(zip(fresh_df['title'], fresh_df['source']))
    new_products      = fresh_df[~fresh_df['_key'].isin(existing_keys)].drop(columns=['_key'])
    fresh_df          = fresh_df.drop(columns=['_key'])

    log.info(f"New products found: {len(new_products)}")
    if not new_products.empty:
        for src, cnt in new_products['source'].value_counts().items():
            log.info(f"  {src}: +{cnt}")

    if new_products.empty:
        log.info("No new products — dataset is current.")
        log.info("=" * 60)
        return

    # 4. save updated datasets
    combined = pd.concat([existing, new_products], ignore_index=True)
    combined.to_csv(COMP_CSV, index=False)
    log.info(f"competitor_products.csv → {len(combined):,} total products")

    cols = ['brand', 'title', 'price', 'source', 'market', 'scraped_date']
    combined[cols].to_csv(MASTER_CSV, index=False)
    log.info(f"master_dataset.csv → {len(combined):,} products")

    log.info("Auto-update complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    run()

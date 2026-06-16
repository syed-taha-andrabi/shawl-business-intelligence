"""
Weekly auto-update pipeline:
  1. Scrape all 13 competitor sites
  2. Find new products not in existing dataset
  3. Append new products to competitor_products.csv
  4. Rebuild master_dataset.csv
  5. Retrain all models if new products were found
  6. Log everything to logs/update_log.txt
"""

import os
import sys
import pickle
import logging
import pandas as pd
from datetime import datetime

# ensure modules/ is on path when run from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from scraper import scrape_all

import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score

# ── paths ────────────────────────────────────────────────────────────────────
ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR    = os.path.join(ROOT, 'data')
MODELS_DIR  = os.path.join(ROOT, 'models')
LOGS_DIR    = os.path.join(ROOT, 'logs')
COMP_CSV    = os.path.join(DATA_DIR, 'competitor_products.csv')
MASTER_CSV  = os.path.join(DATA_DIR, 'master_dataset.csv')
LOG_FILE    = os.path.join(LOGS_DIR, 'update_log.txt')

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


# ── feature engineering (mirrors retrain.py) ─────────────────────────────────
FEATURES = [
    'title_length', 'has_embroidered', 'has_kani', 'has_sozni',
    'has_jamawar', 'has_luxury', 'has_handmade', 'has_authentic',
    'has_cashmere', 'has_wool', 'has_pashmina'
]

def engineer_features(df):
    df = df.copy()
    df['title_length']    = df['title'].str.len()
    df['has_embroidered'] = df['title'].str.lower().str.contains('embroidered').astype(int)
    df['has_kani']        = df['title'].str.lower().str.contains('kani').astype(int)
    df['has_sozni']       = df['title'].str.lower().str.contains('sozni').astype(int)
    df['has_jamawar']     = df['title'].str.lower().str.contains('jamawar').astype(int)
    df['has_luxury']      = df['title'].str.lower().str.contains('luxury').astype(int)
    df['has_handmade']    = df['title'].str.lower().str.contains('handmade').astype(int)
    df['has_authentic']   = df['title'].str.lower().str.contains('authentic').astype(int)
    df['has_cashmere']    = df['title'].str.lower().str.contains('cashmere').astype(int)
    df['has_wool']        = df['title'].str.lower().str.contains('wool').astype(int)
    df['has_pashmina']    = df['title'].str.lower().str.contains('pashmina').astype(int)
    return df


def retrain_for_source(df_source, source_name):
    slug = source_name.lower().replace('.', '_').replace(' ', '_')
    df_source = engineer_features(df_source)

    if len(df_source) < 30:
        log.info(f"  {source_name}: not enough data ({len(df_source)} rows), skipping")
        return

    # price model
    X = df_source[FEATURES]
    y = df_source['price']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    pm = RandomForestRegressor(n_estimators=100, random_state=42)
    pm.fit(X_train, y_train)
    mae = mean_absolute_error(y_test, pm.predict(X_test))
    r2  = r2_score(y_test, pm.predict(X_test))
    log.info(f"  {source_name} price model — MAE: {mae:.0f}, R2: {r2:.3f}, n={len(df_source)}")
    with open(os.path.join(MODELS_DIR, f'price_model_{slug}.pkl'), 'wb') as f:
        pickle.dump(pm, f)
    with open(os.path.join(MODELS_DIR, f'price_features_{slug}.pkl'), 'wb') as f:
        pickle.dump(FEATURES, f)

    # price category classifier
    if source_name in ('Shahkaar', 'Kashmir Loom'):
        bins = [0, 50, 200, 500, float('inf')]
    elif source_name == 'Pashmina.com':
        bins = [0, 50000, 100000, 200000, float('inf')]
    else:
        bins = [0, 1000, 5000, 15000, float('inf')]

    labels = ['Budget', 'Mid-range', 'Premium', 'Luxury']
    df_source = df_source.copy()
    df_source['category'] = pd.cut(df_source['price'], bins=bins, labels=labels)
    df_source = df_source.dropna(subset=['category'])

    if len(df_source) < 30:
        return

    X2 = df_source[FEATURES]
    y2 = df_source['category']
    X_train2, X_test2, y_train2, y_test2 = train_test_split(X2, y2, test_size=0.2, random_state=42)
    cm = RandomForestClassifier(n_estimators=100, random_state=42)
    cm.fit(X_train2, y_train2)
    acc = accuracy_score(y_test2, cm.predict(X_test2))
    log.info(f"  {source_name} classifier  — Accuracy: {acc:.2f}")
    with open(os.path.join(MODELS_DIR, f'classifier_model_{slug}.pkl'), 'wb') as f:
        pickle.dump(cm, f)
    with open(os.path.join(MODELS_DIR, f'classifier_features_{slug}.pkl'), 'wb') as f:
        pickle.dump(FEATURES, f)


def retrain_all(df):
    log.info("Retraining models...")
    for source in df['source'].unique():
        retrain_for_source(df[df['source'] == source].copy(), source)
    log.info("Retraining complete.")


# ── main pipeline ─────────────────────────────────────────────────────────────
def run():
    log.info("=" * 60)
    log.info("Weekly auto-update started")

    # 1. scrape fresh data from all competitors
    log.info("Scraping all 13 competitor sites...")
    fresh_df = scrape_all()
    log.info(f"Scraped {len(fresh_df)} shawl products total")

    # 2. load existing dataset
    if os.path.exists(COMP_CSV):
        existing = pd.read_csv(COMP_CSV)
        existing_keys = set(zip(existing['title'], existing['source']))
    else:
        existing = pd.DataFrame()
        existing_keys = set()

    # 3. find genuinely new products
    fresh_df['_key'] = list(zip(fresh_df['title'], fresh_df['source']))
    new_products = fresh_df[~fresh_df['_key'].isin(existing_keys)].drop(columns=['_key'])
    fresh_df = fresh_df.drop(columns=['_key'])

    log.info(f"New products found: {len(new_products)}")
    if not new_products.empty:
        by_source = new_products['source'].value_counts()
        for src, cnt in by_source.items():
            log.info(f"  {src}: +{cnt}")

    # 4. if nothing new, stop early
    if new_products.empty:
        log.info("No new products — dataset and models are up to date.")
        log.info("=" * 60)
        return

    # 5. append new products and save
    combined = pd.concat([existing, new_products], ignore_index=True)
    combined.to_csv(COMP_CSV, index=False)
    log.info(f"competitor_products.csv updated: {len(combined)} total products")

    cols = ['brand', 'title', 'price', 'source', 'market', 'scraped_date']
    combined[cols].to_csv(MASTER_CSV, index=False)
    log.info(f"master_dataset.csv updated: {len(combined)} products")

    # 6. retrain models on full updated dataset
    master = combined.dropna(subset=['title', 'price'])
    retrain_all(master)

    log.info("Auto-update complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    run()

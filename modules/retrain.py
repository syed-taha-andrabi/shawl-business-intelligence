import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score
import pickle
from datetime import datetime

print(f"Retraining started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

df = pd.read_csv('data/master_dataset.csv')
df = df.dropna(subset=['price', 'title'])

print(f"Total products: {len(df)}")
print(df['source'].value_counts())

def engineer_features(df):
    df = df.copy()
    df['title_length'] = df['title'].str.len()
    df['has_embroidered'] = df['title'].str.lower().str.contains('embroidered').astype(int)
    df['has_kani'] = df['title'].str.lower().str.contains('kani').astype(int)
    df['has_sozni'] = df['title'].str.lower().str.contains('sozni').astype(int)
    df['has_jamawar'] = df['title'].str.lower().str.contains('jamawar').astype(int)
    df['has_luxury'] = df['title'].str.lower().str.contains('luxury').astype(int)
    df['has_handmade'] = df['title'].str.lower().str.contains('handmade').astype(int)
    df['has_authentic'] = df['title'].str.lower().str.contains('authentic').astype(int)
    df['has_cashmere'] = df['title'].str.lower().str.contains('cashmere').astype(int)
    df['has_wool'] = df['title'].str.lower().str.contains('wool').astype(int)
    df['has_pashmina'] = df['title'].str.lower().str.contains('pashmina').astype(int)
    return df

features = [
    'title_length', 'has_embroidered', 'has_kani', 'has_sozni',
    'has_jamawar', 'has_luxury', 'has_handmade', 'has_authentic',
    'has_cashmere', 'has_wool', 'has_pashmina'
]

def train_price_model(df_market, market_name):
    print(f"\nTraining price model for {market_name}...")
    df_market = engineer_features(df_market)
    
    if len(df_market) < 30:
        print(f"Not enough data for {market_name} — skipping")
        return
    
    X = df_market[features]
    y = df_market['price']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    mae = mean_absolute_error(y_test, model.predict(X_test))
    r2 = r2_score(y_test, model.predict(X_test))
    print(f"{market_name} Price Model — MAE: {mae:.0f}, R2: {r2:.3f}, Products: {len(df_market)}")
    
    model_name = market_name.lower().replace('.', '_').replace(' ', '_')
    with open(f'models/price_model_{model_name}.pkl', 'wb') as f:
        pickle.dump(model, f)
    with open(f'models/price_features_{model_name}.pkl', 'wb') as f:
        pickle.dump(features, f)
    
    print(f"Saved: price_model_{model_name}.pkl")

def train_success_model(df_market, market_name):
    print(f"\nTraining success model for {market_name}...")
    df_market = engineer_features(df_market)
    
    if 'rating' not in df_market.columns:
        print(f"No rating data for {market_name} — skipping")
        return
    
    df_market = df_market.dropna(subset=['rating'])
    
    if len(df_market) < 30:
        print(f"Not enough data for {market_name} — skipping")
        return
    
    df_market['success'] = (df_market['rating'] >= 4.7).astype(int)
    
    X = df_market[features]
    y = df_market['success']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"{market_name} Success Model — Accuracy: {acc:.2f}, Products: {len(df_market)}")
    
    model_name = market_name.lower().replace('.', '_').replace(' ', '_')
    with open(f'models/success_model_{model_name}.pkl', 'wb') as f:
        pickle.dump(model, f)
    with open(f'models/success_features_{model_name}.pkl', 'wb') as f:
        pickle.dump(features, f)
    
    print(f"Saved: success_model_{model_name}.pkl")

def train_classifier_model(df_market, market_name):
    print(f"\nTraining category classifier for {market_name}...")
    df_market = engineer_features(df_market)
    
    if len(df_market) < 30:
        print(f"Not enough data for {market_name} — skipping")
        return

    # define price categories per market
    if market_name == 'Amazon.ae':
        bins = [0, 50, 100, 200, float('inf')]
    elif market_name == 'Amazon.in':
        bins = [0, 1000, 5000, 15000, float('inf')]
    else:
        bins = [0, 8000, 25000, 80000, float('inf')]

    labels = ['Budget', 'Mid-range', 'Premium', 'Luxury']
    df_market['category'] = pd.cut(df_market['price'], bins=bins, labels=labels)
    df_market = df_market.dropna(subset=['category'])

    if len(df_market) < 30:
        print(f"Not enough category data for {market_name} — skipping")
        return

    X = df_market[features]
    y = df_market['category']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"{market_name} Classifier — Accuracy: {acc:.2f}, Products: {len(df_market)}")

    model_name = market_name.lower().replace('.', '_').replace(' ', '_')
    with open(f'models/classifier_model_{model_name}.pkl', 'wb') as f:
        pickle.dump(model, f)
    with open(f'models/classifier_features_{model_name}.pkl', 'wb') as f:
        pickle.dump(features, f)

    print(f"Saved: classifier_model_{model_name}.pkl")

# train separate models for each market
for source in df['source'].unique():
    df_market = df[df['source'] == source].copy()
    train_price_model(df_market, source)
    train_success_model(df_market, source)
    train_classifier_model(df_market, source)

print(f"\nAll models retrained: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("\nModels saved:")
import os
for f in os.listdir('models/'):
    print(f"  {f}")

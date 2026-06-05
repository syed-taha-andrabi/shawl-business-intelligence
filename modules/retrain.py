import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score
import pickle
from datetime import datetime

print(f"Retraining started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# load master dataset
df = pd.read_csv('data/master_dataset.csv')
df = df.dropna(subset=['price'])

print(f"Total products for training: {len(df)}")

# feature engineering
df['title_length'] = df['title'].str.len()
df['has_embroidered'] = df['title'].str.lower().str.contains('embroidered').astype(int)
df['has_kani'] = df['title'].str.lower().str.contains('kani').astype(int)
df['has_luxury'] = df['title'].str.lower().str.contains('luxury').astype(int)
df['has_handmade'] = df['title'].str.lower().str.contains('handmade').astype(int)
df['has_authentic'] = df['title'].str.lower().str.contains('authentic').astype(int)
df['is_etsy'] = (df['source'] == 'Etsy').astype(int)
df['is_india'] = (df['market'] == 'India').astype(int)

features = ['title_length', 'has_embroidered', 'has_kani', 'has_luxury',
            'has_handmade', 'has_authentic', 'is_etsy', 'is_india']

# ===== RETRAIN PRICE MODEL =====
print("\nRetraining price model...")
X = df[features]
y = df['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
price_model = RandomForestRegressor(n_estimators=100, random_state=42)
price_model.fit(X_train, y_train)

mae = mean_absolute_error(y_test, price_model.predict(X_test))
r2 = r2_score(y_test, price_model.predict(X_test))
print(f"Price Model — MAE: {mae:.0f}, R2: {r2:.3f}")

with open('models/price_model.pkl', 'wb') as f:
    pickle.dump(price_model, f)
with open('models/price_features.pkl', 'wb') as f:
    pickle.dump(features, f)

# ===== RETRAIN SUCCESS MODEL =====
print("\nRetraining success model...")
df_etsy = pd.read_csv('data/etsy_clean.csv')
df_etsy = df_etsy.dropna(subset=['sale_price', 'rating'])
df_etsy['success'] = (df_etsy['rating'] >= 4.7).astype(int)
df_etsy['title_length'] = df_etsy['title'].str.len()
df_etsy['has_embroidered'] = df_etsy['title'].str.lower().str.contains('embroidered').astype(int)
df_etsy['has_kani'] = df_etsy['title'].str.lower().str.contains('kani').astype(int)
df_etsy['has_luxury'] = df_etsy['title'].str.lower().str.contains('luxury').astype(int)
df_etsy['has_handmade'] = df_etsy['title'].str.lower().str.contains('handmade').astype(int)
df_etsy['has_authentic'] = df_etsy['title'].str.lower().str.contains('authentic').astype(int)
df_etsy['discount_pct'] = df_etsy['discount'].str.replace('(','').str.replace('% off)','').str.strip()
df_etsy['discount_pct'] = pd.to_numeric(df_etsy['discount_pct'], errors='coerce').fillna(0)

success_features = ['sale_price', 'title_length', 'has_embroidered', 'has_kani',
                    'has_luxury', 'has_handmade', 'has_authentic', 'discount_pct']

X_s = df_etsy[success_features]
y_s = df_etsy['success']

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X_s, y_s, test_size=0.2, random_state=42)
success_model = RandomForestClassifier(n_estimators=100, random_state=42)
success_model.fit(X_train_s, y_train_s)

acc = accuracy_score(y_test_s, success_model.predict(X_test_s))
print(f"Success Model — Accuracy: {acc:.2f}")

with open('models/success_model.pkl', 'wb') as f:
    pickle.dump(success_model, f)
with open('models/success_features.pkl', 'wb') as f:
    pickle.dump(success_features, f)

print(f"\nAll models retrained and saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

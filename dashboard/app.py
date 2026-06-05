import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Kashmir Shawl Business Intelligence",
    page_icon="🏔️",
    layout="wide"
)

st.title("🏔️ Kashmir Shawl Business Intelligence")
st.subheader("Market Analysis Dashboard — Andrab Gallery")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "Market Overview",
    "Competitor Analysis",
    "Demand Calendar",
    "Product Analyzer"
])

if page == "Market Overview":
    st.header("📊 Market Overview")
    df = pd.read_csv('data/master_dataset.csv')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Competitors", df['brand'].nunique())
    col2.metric("Total Products", len(df))
    col3.metric("Avg Price (₹)", f"₹{df['price'].mean():.0f}")
    col4.metric("Platforms", df['source'].nunique())
    st.divider()
    st.subheader("Price Distribution")
    fig, ax = plt.subplots(figsize=(10, 4))
    etsy = df[df['source']=='Etsy']['price']
    amazon = df[df['source']=='Amazon.ae']['price']
    ax.hist(etsy, bins=15, alpha=0.7, color='steelblue', label='Etsy')
    ax.hist(amazon, bins=15, alpha=0.7, color='coral', label='Amazon.ae')
    ax.set_xlabel('Price (₹)')
    ax.set_ylabel('Number of Products')
    ax.legend()
    st.pyplot(fig)

elif page == "Competitor Analysis":
    st.header("🏪 Competitor Analysis")
    df = pd.read_csv('data/master_dataset.csv')
    platform = st.selectbox("Select Platform", ["All", "Etsy", "Amazon.ae"])
    if platform != "All":
        df = df[df['source'] == platform]
    st.subheader("Top Brands by Listings")
    top_brands = df['brand'].value_counts().head(10)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top_brands.index, top_brands.values, color='steelblue')
    ax.set_xlabel('Number of Listings')
    st.pyplot(fig)
    st.divider()
    st.subheader("Average Price by Brand (Top 10)")
    avg_price = df.groupby('brand')['price'].mean().sort_values(ascending=False).head(10)
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.barh(avg_price.index, avg_price.values, color='coral')
    ax2.set_xlabel('Average Price (₹)')
    st.pyplot(fig2)

elif page == "Demand Calendar":
    st.header("📅 Demand Calendar")
    
    df_trends = pd.read_csv('data/trends_all_regions.csv')
    df_trends['date'] = pd.to_datetime(df_trends['date'])
    
    st.subheader("Search Interest by Region")
    
    fig, ax = plt.subplots(figsize=(12, 5))
    for region in df_trends['region'].unique():
        data = df_trends[df_trends['region'] == region]
        ax.plot(data['date'], data['interest'], label=region, linewidth=2)
    
    ax.set_xlabel('Date')
    ax.set_ylabel('Search Interest')
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    
    st.divider()
    
    st.subheader("📊 Monthly Business Advice")
    
    month_names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    advice = {
        'Jan': ('🔥 PEAK', 'Run promotions, max stock, push ads'),
        'Feb': ('📈 GROWING', 'Maintain momentum, keep stocking'),
        'Mar': ('❄️ LOW', 'Focus on new designs'),
        'Apr': ('❄️ LOW', 'Focus on new designs'),
        'May': ('➡️ MODERATE', 'Maintain presence'),
        'Jun': ('➡️ MODERATE', 'Maintain presence'),
        'Jul': ('❄️ LOW', 'Prepare for upcoming season'),
        'Aug': ('📈 GROWING', 'Start stocking up'),
        'Sep': ('📈 GROWING', 'Prepare listings and inventory'),
        'Oct': ('➡️ MODERATE', 'Final prep for peak season'),
        'Nov': ('🔥 PEAK', 'Run promotions, max stock, push ads'),
        'Dec': ('🔥 PEAK', 'Run promotions, max stock, push ads'),
    }
    
    cols = st.columns(4)
    for i, month in enumerate(month_names):
        with cols[i % 4]:
            status, tip = advice[month]
            st.metric(month, status)
            st.caption(tip)


elif page == "Product Analyzer":
    st.header("🔍 Product Analyzer")
    st.write("Enter your product details to get AI-powered insights")
    
    import pickle
    import numpy as np
    
    # load models
    with open('models/price_model.pkl', 'rb') as f:
        price_model = pickle.load(f)
    with open('models/price_features.pkl', 'rb') as f:
        price_features = pickle.load(f)
    with open('models/success_model.pkl', 'rb') as f:
        success_model = pickle.load(f)
    with open('models/success_features.pkl', 'rb') as f:
        success_features = pickle.load(f)
    with open('models/classifier_model.pkl', 'rb') as f:
        classifier_model = pickle.load(f)
    with open('models/classifier_features.pkl', 'rb') as f:
        classifier_features = pickle.load(f)

    title = st.text_input("Product Title", placeholder="e.g. Authentic Hand Embroidered Kani Pashmina Shawl")
    price = st.number_input("Your Price (₹)", min_value=0, value=25000, step=500)
    discount = st.number_input("Discount %", min_value=0, max_value=80, value=20)
    rating = st.slider("Expected Rating", 1.0, 5.0, 4.5, 0.1)

    if st.button("Analyze Product"):
        if title:
            # prepare features
            title_length = len(title)
            has_embroidered = 1 if 'embroidered' in title.lower() else 0
            has_kani = 1 if 'kani' in title.lower() else 0
            has_luxury = 1 if 'luxury' in title.lower() else 0
            has_handmade = 1 if 'handmade' in title.lower() else 0
            has_authentic = 1 if 'authentic' in title.lower() else 0

            # price prediction
            price_input = pd.DataFrame([[rating, title_length, has_embroidered, has_kani,
                                         has_luxury, has_handmade, has_authentic, discount]],
                                         columns=price_features)
            predicted_price = price_model.predict(price_input)[0]

            # success prediction
            success_input = pd.DataFrame([[price, title_length, has_embroidered, has_kani,
                                           has_luxury, has_handmade, has_authentic, discount]],
                                           columns=success_features)
            success_pred = success_model.predict(success_input)[0]
            success_prob = success_model.predict_proba(success_input)[0][1] * 100

            # category prediction
            cat_input = pd.DataFrame([[title_length, has_embroidered, has_kani, has_luxury,
                                       has_handmade, has_authentic, discount]],
                                       columns=classifier_features)
            category = classifier_model.predict(cat_input)[0]

            # display results
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Suggested Price", f"₹{predicted_price:,.0f}")
            col2.metric("Success Probability", f"{success_prob:.0f}%")
            col3.metric("Price Category", category)

            st.divider()

            if success_pred == 1:
                st.success(f"🔥 HIGH PERFORMER — {success_prob:.0f}% chance of success on Etsy")
            else:
                st.error(f"❌ LOW PERFORMER — Only {success_prob:.0f}% chance of success. Improve your title.")

            # keyword tips
            keywords_found = [kw for kw in ['embroidered', 'kani', 'luxury', 'handmade', 'authentic', 'pashmina', 'sozni'] 
                             if kw in title.lower()]
            missing = [kw for kw in ['embroidered', 'authentic', 'handmade', 'kani'] 
                      if kw not in title.lower()]

            if keywords_found:
                st.success(f"✅ Strong keywords: {', '.join(keywords_found)}")
            if missing:
                st.warning(f"⚠️ Consider adding: {', '.join(missing)}")
        else:
            st.warning("Please enter a product title")
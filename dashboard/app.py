import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pickle
import os
from collections import Counter
import re

st.set_page_config(
    page_title="Kashmir Shawl Business Intelligence",
    page_icon="🏔️",
    layout="wide"
)

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(ROOT, 'data')
MODELS_DIR = os.path.join(ROOT, 'models')

SHAWL_KEYWORDS = [
    'pashmina', 'kani', 'sozni', 'jamawar', 'embroidered', 'cashmere',
    'wool', 'handmade', 'handwoven', 'authentic', 'luxury', 'aari',
    'tilla', 'pure', 'kashmiri', 'kashmir', 'stole', 'shawl', 'wrap',
    'scarf', 'dorukha', 'reversible', 'printed', 'plain'
]

PRICE_BINS   = [0, 1000, 5000, 15000, 50000, float('inf')]
PRICE_LABELS = ['Under ₹1K', '₹1K–5K', '₹5K–15K', '₹15K–50K', '₹50K+']

COLORS = [
    '#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3',
    '#937860', '#DA8BC3', '#8C8C8C', '#CCB974', '#64B5CD',
    '#2196F3', '#FF5722', '#9C27B0'
]

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, 'competitor_products.csv'))
    df = df.dropna(subset=['title', 'price'])
    df['price_segment'] = pd.cut(df['price'], bins=PRICE_BINS, labels=PRICE_LABELS)
    return df

@st.cache_data
def load_trends():
    path = os.path.join(DATA_DIR, 'trends_all_regions.csv')
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df

def extract_keywords(titles):
    counts = Counter()
    for title in titles:
        words = re.findall(r'\b\w+\b', title.lower())
        for w in words:
            if w in SHAWL_KEYWORDS:
                counts[w] += 1
    return counts

def fmt_price(val):
    if val >= 1_00_000:
        return f"₹{val/1_00_000:.1f}L"
    elif val >= 1000:
        return f"₹{val/1000:.0f}K"
    return f"₹{val:.0f}"

# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/emoji/96/mountain-snow.png", width=60)
st.sidebar.title("Kashmir Shawl BI")
st.sidebar.caption("Andrab Gallery — Market Intelligence")
st.sidebar.divider()

page = st.sidebar.radio("", [
    "📊 Market Overview",
    "🏪 Competitor Deep Dive",
    "💡 Market Gaps",
    "📅 Demand Calendar",
    "🔍 Product Analyzer",
])

df = load_data()
sources = sorted(df['source'].unique())

# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Market Overview":
    st.title("📊 Market Overview")
    st.caption(f"Data from {df['scraped_date'].max()} | {len(sources)} competitors tracked")

    # ── top metrics ──────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Products",    f"{len(df):,}")
    c2.metric("Competitors",       len(sources))
    c3.metric("Avg Price",         fmt_price(df['price'].mean()))
    c4.metric("Median Price",      fmt_price(df['price'].median()))
    c5.metric("Price Range",       f"{fmt_price(df['price'].min())} – {fmt_price(df['price'].max())}")

    st.divider()

    col_left, col_right = st.columns(2)

    # ── products per competitor ───────────────────────────────────────────────
    with col_left:
        st.subheader("Products per Competitor")
        counts = df['source'].value_counts()
        fig, ax = plt.subplots(figsize=(7, 5))
        bars = ax.barh(counts.index[::-1], counts.values[::-1],
                       color=COLORS[:len(counts)])
        for bar, val in zip(bars, counts.values[::-1]):
            ax.text(bar.get_width() + 20, bar.get_y() + bar.get_height()/2,
                    f'{val:,}', va='center', fontsize=9)
        ax.set_xlabel('Number of Products')
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)

    # ── avg price per competitor ──────────────────────────────────────────────
    with col_right:
        st.subheader("Average Price by Competitor")
        avg = df.groupby('source')['price'].mean().sort_values(ascending=True)
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        bars2 = ax2.barh(avg.index, avg.values, color=COLORS[:len(avg)])
        for bar, val in zip(bars2, avg.values):
            ax2.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
                     fmt_price(val), va='center', fontsize=9)
        ax2.set_xlabel('Average Price (₹)')
        ax2.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2)

    st.divider()

    col3, col4 = st.columns(2)

    # ── price segment distribution ────────────────────────────────────────────
    with col3:
        st.subheader("Market by Price Segment")
        seg = df['price_segment'].value_counts().reindex(PRICE_LABELS).fillna(0)
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        wedges, texts, autotexts = ax3.pie(
            seg.values, labels=seg.index, autopct='%1.1f%%',
            colors=COLORS[:len(seg)], startangle=90
        )
        for at in autotexts:
            at.set_fontsize(9)
        plt.tight_layout()
        st.pyplot(fig3)

    # ── top keywords across all competitors ───────────────────────────────────
    with col4:
        st.subheader("Top Keywords in Competitor Titles")
        kw = extract_keywords(df['title'])
        kw_df = pd.DataFrame(kw.most_common(15), columns=['keyword', 'count'])
        fig4, ax4 = plt.subplots(figsize=(7, 4))
        ax4.barh(kw_df['keyword'][::-1], kw_df['count'][::-1], color='#4C72B0')
        ax4.set_xlabel('Frequency')
        ax4.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig4)


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏪 Competitor Deep Dive":
    st.title("🏪 Competitor Deep Dive")

    competitor = st.selectbox("Select Competitor", sources)
    df_c = df[df['source'] == competitor]

    # ── metrics ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Products",     f"{len(df_c):,}")
    c2.metric("Avg Price",    fmt_price(df_c['price'].mean()))
    c3.metric("Median Price", fmt_price(df_c['price'].median()))
    c4.metric("Lowest",       fmt_price(df_c['price'].min()))
    c5.metric("Highest",      fmt_price(df_c['price'].max()))

    st.divider()
    col_l, col_r = st.columns(2)

    # ── price distribution ────────────────────────────────────────────────────
    with col_l:
        st.subheader(f"Price Distribution — {competitor}")
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(df_c['price'], bins=30, color='#4C72B0', edgecolor='white')
        ax.axvline(df_c['price'].mean(),   color='#DD8452', linewidth=2, label='Mean')
        ax.axvline(df_c['price'].median(), color='#55A868', linewidth=2, linestyle='--', label='Median')
        ax.set_xlabel('Price (₹)')
        ax.set_ylabel('Products')
        ax.legend()
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: fmt_price(x)))
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)

    # ── keywords ──────────────────────────────────────────────────────────────
    with col_r:
        st.subheader(f"Keywords — {competitor}")
        kw = extract_keywords(df_c['title'])
        kw_df = pd.DataFrame(kw.most_common(12), columns=['keyword', 'count'])
        if not kw_df.empty:
            fig2, ax2 = plt.subplots(figsize=(7, 4))
            ax2.barh(kw_df['keyword'][::-1], kw_df['count'][::-1], color='#DD8452')
            ax2.set_xlabel('Frequency')
            ax2.spines[['top','right']].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig2)

    st.divider()

    # ── price segments ────────────────────────────────────────────────────────
    st.subheader(f"Price Segments — {competitor}")
    seg = df_c['price_segment'].value_counts().reindex(PRICE_LABELS).fillna(0)
    fig3, ax3 = plt.subplots(figsize=(10, 3))
    bars = ax3.bar(seg.index, seg.values, color=COLORS[:len(seg)])
    for bar, val in zip(bars, seg.values):
        if val > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     int(val), ha='center', fontsize=10)
    ax3.set_ylabel('Products')
    ax3.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig3)

    st.divider()

    # ── top brands within competitor ──────────────────────────────────────────
    if df_c['brand'].nunique() > 1:
        st.subheader(f"Top Brands — {competitor}")
        top_brands = df_c['brand'].value_counts().head(10)
        fig4, ax4 = plt.subplots(figsize=(10, 3))
        ax4.bar(top_brands.index, top_brands.values, color='#8172B3')
        ax4.set_ylabel('Products')
        ax4.tick_params(axis='x', rotation=30)
        ax4.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig4)

    # ── sample products ───────────────────────────────────────────────────────
    st.subheader(f"Sample Products — {competitor}")
    show_cols = ['title', 'price', 'brand', 'product_type']
    show_cols = [c for c in show_cols if c in df_c.columns]
    st.dataframe(
        df_c[show_cols].sort_values('price', ascending=False).head(20),
        use_container_width=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💡 Market Gaps":
    st.title("💡 Market Gaps & Opportunities")
    st.caption("Where competition is thin — potential entry points for Andrab Gallery")

    col_l, col_r = st.columns(2)

    # ── price segment gaps ────────────────────────────────────────────────────
    with col_l:
        st.subheader("Competition Density by Price Segment")
        seg_all = df['price_segment'].value_counts().reindex(PRICE_LABELS).fillna(0)
        fig, ax = plt.subplots(figsize=(7, 4))
        colors_gap = ['#C44E52' if v > seg_all.mean() else '#55A868' for v in seg_all.values]
        bars = ax.bar(seg_all.index, seg_all.values, color=colors_gap)
        for bar, val in zip(bars, seg_all.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    int(val), ha='center', fontsize=10)
        ax.axhline(seg_all.mean(), color='gray', linestyle='--', linewidth=1, label='Average')
        ax.set_ylabel('Products')
        ax.legend()
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)
        st.caption("🟢 Green = low competition (opportunity) | 🔴 Red = crowded")

    # ── keyword gap ───────────────────────────────────────────────────────────
    with col_r:
        st.subheader("Underused Keywords in Competitor Titles")
        kw_counts = extract_keywords(df['title'])
        total = len(df)
        kw_df = pd.DataFrame(
            [(k, kw_counts.get(k, 0), round(kw_counts.get(k, 0)/total*100, 1))
             for k in SHAWL_KEYWORDS],
            columns=['keyword', 'count', 'pct']
        ).sort_values('pct')
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        colors_kw = ['#55A868' if p < 5 else '#4C72B0' if p < 20 else '#C44E52'
                     for p in kw_df['pct']]
        ax2.barh(kw_df['keyword'], kw_df['pct'], color=colors_kw)
        ax2.set_xlabel('% of competitor products using this keyword')
        ax2.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2)
        st.caption("🟢 Green = rarely used by competitors = differentiation opportunity")

    st.divider()

    # ── price gap finder ──────────────────────────────────────────────────────
    st.subheader("Price Range Gap Finder")
    st.caption("Fine-grained price buckets — find where competitors have thin coverage")

    max_price = int(df['price'].quantile(0.95))
    bucket_size = st.slider("Bucket size (₹)", 500, 5000, 1000, step=500)
    buckets = range(0, max_price + bucket_size, bucket_size)
    df['bucket'] = pd.cut(df['price'], bins=list(buckets), right=False)
    bucket_counts = df['bucket'].value_counts().sort_index()

    fig3, ax3 = plt.subplots(figsize=(14, 4))
    colors_b = ['#C44E52' if v > bucket_counts.mean() else
                '#55A868' if v < bucket_counts.mean() * 0.3 else '#4C72B0'
                for v in bucket_counts.values]
    ax3.bar(range(len(bucket_counts)), bucket_counts.values, color=colors_b)
    ax3.set_xticks(range(0, len(bucket_counts), max(1, len(bucket_counts)//12)))
    ax3.set_xticklabels(
        [str(b.left//1000)+'K' for b in bucket_counts.index[::max(1, len(bucket_counts)//12)]],
        rotation=45
    )
    ax3.set_xlabel('Price Range (₹)')
    ax3.set_ylabel('Competitor Products')
    ax3.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig3)

    # ── low competition segments ───────────────────────────────────────────────
    threshold = bucket_counts.mean() * 0.3
    gaps = bucket_counts[bucket_counts < threshold]
    if not gaps.empty:
        st.success(f"**{len(gaps)} price ranges with very low competition:**")
        gap_strs = [f"₹{int(b.left):,} – ₹{int(b.right):,}" for b in gaps.index]
        st.write(" | ".join(gap_strs[:10]))
    else:
        st.info("No major price gaps detected at this bucket size. Try a smaller bucket.")

    st.divider()

    # ── competitor comparison matrix ──────────────────────────────────────────
    st.subheader("Competitor Segment Matrix")
    matrix = df.groupby(['source', 'price_segment']).size().unstack(fill_value=0)
    matrix = matrix.reindex(columns=PRICE_LABELS, fill_value=0)
    fig4, ax4 = plt.subplots(figsize=(12, 5))
    im = ax4.imshow(matrix.values, cmap='YlOrRd', aspect='auto')
    ax4.set_xticks(range(len(PRICE_LABELS)))
    ax4.set_xticklabels(PRICE_LABELS, rotation=20)
    ax4.set_yticks(range(len(matrix.index)))
    ax4.set_yticklabels(matrix.index)
    for i in range(len(matrix.index)):
        for j in range(len(PRICE_LABELS)):
            val = matrix.values[i][j]
            if val > 0:
                ax4.text(j, i, str(val), ha='center', va='center',
                         color='white' if val > matrix.values.max()*0.6 else 'black',
                         fontsize=8)
    plt.colorbar(im, ax=ax4, label='Products')
    plt.tight_layout()
    st.pyplot(fig4)
    st.caption("Dark = many products (crowded). White/light = few products (opportunity).")


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Demand Calendar":
    st.title("📅 Demand Calendar")

    try:
        df_trends = load_trends()
        st.subheader("Pashmina Search Interest by Region")
        fig, ax = plt.subplots(figsize=(12, 5))
        for i, region in enumerate(df_trends['region'].unique()):
            data = df_trends[df_trends['region'] == region]
            ax.plot(data['date'], data['interest'], label=region,
                    linewidth=2, color=COLORS[i % len(COLORS)])
        ax.set_xlabel('Date')
        ax.set_ylabel('Search Interest (0–100)')
        ax.legend()
        ax.spines[['top','right']].set_visible(False)
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Trends data unavailable: {e}")

    st.divider()
    st.subheader("📆 Monthly Strategy Guide")

    advice = {
        'Jan':  ('🔥 PEAK SEASON',    '#C44E52', 'Maximum stock, run ads, push premium products'),
        'Feb':  ('📈 STRONG',          '#DD8452', 'Maintain momentum, keep inventory full'),
        'Mar':  ('📉 SLOWING',         '#8172B3', 'Focus on new designs, plan next collection'),
        'Apr':  ('❄️ LOW',             '#4C72B0', 'Product development, photography, listings'),
        'May':  ('➡️ MODERATE',        '#55A868', 'Maintain presence, test new keywords'),
        'Jun':  ('➡️ MODERATE',        '#55A868', 'Mid-year review, prep summer wraps'),
        'Jul':  ('❄️ LOW',             '#4C72B0', 'Stock up raw materials, plan autumn range'),
        'Aug':  ('📈 BUILDING',        '#DD8452', 'Start stocking, launch pre-season listings'),
        'Sep':  ('📈 GROWING',         '#DD8452', 'Push listings, prepare gifting bundles'),
        'Oct':  ('🔥 PRE-PEAK',        '#C44E52', 'Full stock, aggressive ads, festival offers'),
        'Nov':  ('🔥 PEAK SEASON',     '#C44E52', 'Maximum stock, run ads, push premium products'),
        'Dec':  ('🔥 PEAK SEASON',     '#C44E52', 'Gift season — bundles, express shipping, premium'),
    }

    cols = st.columns(4)
    for i, (month, (status, color, tip)) in enumerate(advice.items()):
        with cols[i % 4]:
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:8px;margin:4px 0;border-radius:4px'>"
                f"<b>{month}</b><br><span style='color:{color}'>{status}</span>"
                f"<br><small>{tip}</small></div>",
                unsafe_allow_html=True
            )


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Product Analyzer":
    st.title("🔍 Product Analyzer")
    st.caption("Benchmark your product against any competitor's market data")

    # keywords that must appear for a title to count as a shawl product
    SHAWL_CORE = {
        'shawl', 'stole', 'pashmina', 'cashmere', 'wrap', 'scarf',
        'kani', 'sozni', 'jamawar', 'kashmiri', 'kashmir',
        'aari', 'tilla', 'dorukha', 'wool', 'dupatta'
    }
    # keywords that boost confidence (nice-to-have, not required)
    SHAWL_QUALITY = {
        'embroidered', 'handmade', 'handwoven', 'authentic', 'luxury',
        'pure', 'reversible', 'printed', 'plain', 'hashida'
    }

    col_input, col_result = st.columns([1, 1])

    with col_input:
        title = st.text_input(
            "Your Product Title",
            placeholder="e.g. Hand Embroidered Kani Pashmina Shawl Women"
        )
        market = st.selectbox("Benchmark Against", sources)
        your_price = st.number_input("Your Price (₹)", min_value=0, value=15000, step=500)
        analyze = st.button("Analyze", use_container_width=True)

    if analyze and not title:
        with col_result:
            st.error("Please enter a product title.")

    elif analyze and title:
        t = title.lower()

        # ── shawl validation ─────────────────────────────────────────────────
        core_hits    = [k for k in SHAWL_CORE    if k in t]
        quality_hits = [k for k in SHAWL_QUALITY if k in t]
        confidence   = len(core_hits) * 2 + len(quality_hits)  # weighted score

        with col_result:
            if not core_hits:
                st.error(
                    "**This doesn't look like a shawl/pashmina product.**\n\n"
                    "The title must contain at least one of: "
                    + ", ".join(sorted(SHAWL_CORE))
                )
                st.stop()

            # confidence badge
            if confidence >= 4:
                badge_color, badge_text = '#55A868', f'High confidence ({confidence}/10)'
            elif confidence >= 2:
                badge_color, badge_text = '#DD8452', f'Medium confidence ({confidence}/10)'
            else:
                badge_color, badge_text = '#8172B3', f'Low confidence ({confidence}/10) — add more keywords'

            st.markdown(
                f"<div style='background:{badge_color};color:white;padding:6px 12px;"
                f"border-radius:6px;display:inline-block;margin-bottom:12px'>"
                f"Shawl confidence: {badge_text}</div>",
                unsafe_allow_html=True
            )

            # ── load models ──────────────────────────────────────────────────
            slug = market.lower().replace('.', '_').replace(' ', '_')
            price_model_path    = os.path.join(MODELS_DIR, f'price_model_{slug}.pkl')
            price_features_path = os.path.join(MODELS_DIR, f'price_features_{slug}.pkl')
            class_model_path    = os.path.join(MODELS_DIR, f'classifier_model_{slug}.pkl')
            class_features_path = os.path.join(MODELS_DIR, f'classifier_features_{slug}.pkl')

            models_ok = all(os.path.exists(p) for p in [
                price_model_path, price_features_path, class_model_path, class_features_path
            ])

            features = {
                'title_length':    len(title),
                'has_embroidered': int('embroidered' in t),
                'has_kani':        int('kani' in t),
                'has_sozni':       int('sozni' in t),
                'has_jamawar':     int('jamawar' in t),
                'has_luxury':      int('luxury' in t),
                'has_handmade':    int('handmade' in t or 'handwoven' in t),
                'has_authentic':   int('authentic' in t),
                'has_cashmere':    int('cashmere' in t),
                'has_wool':        int('wool' in t),
                'has_pashmina':    int('pashmina' in t),
            }

            if models_ok:
                with open(price_model_path, 'rb') as f:    pm = pickle.load(f)
                with open(price_features_path, 'rb') as f: pf = pickle.load(f)
                with open(class_model_path, 'rb') as f:    cm = pickle.load(f)
                with open(class_features_path, 'rb') as f: cf = pickle.load(f)

                X_price = pd.DataFrame([[features[k] for k in pf]], columns=pf)
                X_class = pd.DataFrame([[features[k] for k in cf]], columns=cf)

                suggested_price = pm.predict(X_price)[0]
                category = cm.predict(X_class)[0]

                st.subheader("Price Estimate")
                m1, m2, m3 = st.columns(3)
                m1.metric("Model Estimate",  fmt_price(suggested_price))
                m2.metric("Your Price",      fmt_price(your_price))
                delta = your_price - suggested_price
                m3.metric("vs Model",        fmt_price(abs(delta)),
                          delta=f"{'over' if delta > 0 else 'under'} estimate",
                          delta_color="inverse")
                st.caption(f"Category: **{category}** — trained on {market} product prices")

            # ── actual market data for matching keywords ───────────────────
            df_m = df[df['source'] == market].copy()

            # filter competitor products to those sharing ≥1 core keyword
            mask = df_m['title'].str.lower().apply(
                lambda x: any(k in x for k in core_hits)
            )
            df_similar = df_m[mask]

            st.divider()
            st.subheader(f"Similar Products in {market}")
            c1, c2, c3, c4 = st.columns(4)
            if not df_similar.empty:
                c1.metric("Matched Products", f"{len(df_similar):,}")
                c2.metric("Avg Price",         fmt_price(df_similar['price'].mean()))
                c3.metric("Lowest",            fmt_price(df_similar['price'].min()))
                c4.metric("Highest",           fmt_price(df_similar['price'].max()))

                pct = (df_similar['price'] < your_price).mean() * 100
                st.write(
                    f"Your price **{fmt_price(your_price)}** is higher than "
                    f"**{pct:.0f}%** of similar products on {market}."
                )
                st.dataframe(
                    df_similar[['title', 'price']].sort_values('price', ascending=False).head(10),
                    use_container_width=True, hide_index=True
                )
            else:
                c1.metric("Matched Products", "0")
                st.info(f"No products with these keywords found on {market}.")

            # ── keyword analysis ──────────────────────────────────────────
            st.divider()
            st.subheader("Keyword Breakdown")

            all_hits = core_hits + quality_hits
            missing_core    = [k for k in ['pashmina','kani','sozni','embroidered',
                                            'cashmere','handmade','kashmiri','shawl']
                               if k not in t]

            if all_hits:
                st.success(f"Found: **{', '.join(all_hits)}**")
            if missing_core:
                st.warning(f"Consider adding: **{', '.join(missing_core)}**")

            kw_mkt    = extract_keywords(df_m['title'])
            total_mkt = len(df_m)
            if all_hits:
                kw_compare = pd.DataFrame(
                    [(k, kw_mkt.get(k, 0), round(kw_mkt.get(k, 0)/total_mkt*100, 1))
                     for k in all_hits],
                    columns=['keyword', 'count', '% of competitor titles']
                ).sort_values('% of competitor titles', ascending=False)
                st.dataframe(kw_compare, use_container_width=True, hide_index=True)

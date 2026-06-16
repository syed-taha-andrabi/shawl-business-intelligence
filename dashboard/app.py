import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
import os
import re
from collections import Counter

st.set_page_config(
    page_title="Kashmir Shawl Intelligence",
    page_icon="🏔️",
    layout="wide"
)

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')

SHAWL_KEYWORDS = [
    'pashmina', 'kani', 'sozni', 'jamawar', 'embroidered', 'cashmere',
    'wool', 'handmade', 'handwoven', 'authentic', 'luxury', 'aari',
    'tilla', 'pure', 'kashmiri', 'kashmir', 'stole', 'shawl', 'wrap',
    'scarf', 'dorukha', 'reversible', 'printed', 'plain', 'woven',
]

PRICE_BINS   = [0, 1000, 5000, 15000, 50000, float('inf')]
PRICE_LABELS = ['<₹1K', '₹1K–5K', '₹5K–15K', '₹15K–50K', '₹50K+']

PALETTE = [
    '#2196F3','#FF5722','#4CAF50','#9C27B0','#FF9800',
    '#00BCD4','#F44336','#8BC34A','#673AB7','#03A9F4',
    '#E91E63','#CDDC39','#795548','#607D8B',
]

# ── helpers ───────────────────────────────────────────────────────────────────
def fmt_price(v):
    if v >= 1_00_000: return f"₹{v/1_00_000:.1f}L"
    if v >= 1_000:    return f"₹{v/1_000:.0f}K"
    return f"₹{v:.0f}"

def kw_flags(titles):
    result = {k: [] for k in SHAWL_KEYWORDS}
    for t in titles:
        tl = t.lower()
        for k in SHAWL_KEYWORDS:
            result[k].append(int(k in tl))
    return pd.DataFrame(result)

@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, 'competitor_products.csv'))
    df = df.dropna(subset=['title','price'])
    df['price']    = pd.to_numeric(df['price'],    errors='coerce')
    df['orig']     = pd.to_numeric(df.get('original_price', np.nan), errors='coerce')
    df = df.dropna(subset=['price'])
    df['price_seg'] = pd.cut(df['price'], bins=PRICE_BINS, labels=PRICE_LABELS)
    df['title_len'] = df['title'].str.len()
    df['discount_pct'] = np.where(
        df['orig'].notna() & (df['orig'] > df['price']),
        (df['orig'] - df['price']) / df['orig'] * 100,
        np.nan
    )
    return df

@st.cache_data
def load_trends():
    path = os.path.join(DATA_DIR, 'trends_all_regions.csv')
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    return df

@st.cache_data
def keyword_matrix(df):
    """Returns (sources × keywords) matrix of % of products containing each keyword."""
    sources = df['source'].unique()
    mat = {}
    for src in sources:
        titles = df[df['source']==src]['title'].tolist()
        total  = len(titles)
        row    = {}
        for kw in SHAWL_KEYWORDS:
            count = sum(1 for t in titles if kw in t.lower())
            row[kw] = round(count/total*100, 1) if total > 0 else 0
        mat[src] = row
    return pd.DataFrame(mat).T  # rows=sources, cols=keywords

@st.cache_data
def keyword_price_impact(df):
    """For each keyword: avg price WITH keyword vs WITHOUT — returns the premium."""
    rows = []
    global_avg = df['price'].mean()
    for kw in SHAWL_KEYWORDS:
        mask   = df['title'].str.lower().str.contains(kw, na=False)
        n_with = mask.sum()
        if n_with < 10:
            continue
        avg_with    = df[mask]['price'].mean()
        avg_without = df[~mask]['price'].mean()
        rows.append({
            'keyword':     kw,
            'n_products':  int(n_with),
            'avg_price_with':    round(avg_with, 0),
            'avg_price_without': round(avg_without, 0),
            'price_premium':     round(avg_with - avg_without, 0),
            'pct_premium':       round((avg_with - avg_without)/avg_without*100, 1),
        })
    return pd.DataFrame(rows).sort_values('price_premium', ascending=False)

@st.cache_data
def competition_scores(df):
    """Intensity score per (source, price_segment): higher = more crowded."""
    total = len(df)
    grp = df.groupby(['source','price_seg']).size().reset_index(name='n_products')
    seg_totals = df.groupby('price_seg').size().reset_index(name='seg_total')
    grp = grp.merge(seg_totals, on='price_seg')
    grp['intensity'] = (grp['n_products'] / grp['seg_total'] * 100).round(1)
    return grp


# ── sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.title("🏔️ Kashmir Shawl BI")
st.sidebar.caption("Andrab Gallery — Market Intelligence")
st.sidebar.divider()

page = st.sidebar.radio("Navigation", [
    "📊 Market Overview",
    "🏪 Competitor Deep Dive",
    "💰 Price Intelligence",
    "🔤 Keyword Intelligence",
    "💡 Market Gaps",
    "📅 Demand Calendar",
])

df      = load_data()
sources = sorted(df['source'].unique())
n_src   = len(sources)

# ═══════════════════════════════════════════════════════════════════════════════
if page == "📊 Market Overview":
    st.title("📊 Market Overview")
    last_scrape = df['scraped_date'].max() if 'scraped_date' in df.columns else 'unknown'
    st.caption(f"Last scraped: {last_scrape} | {n_src} competitors | {len(df):,} products")

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Products",       f"{len(df):,}")
    k2.metric("Competitors",    n_src)
    k3.metric("Avg Price",      fmt_price(df['price'].mean()))
    k4.metric("Median Price",   fmt_price(df['price'].median()))
    k5.metric("Lowest",         fmt_price(df['price'].min()))
    k6.metric("Highest",        fmt_price(df['price'].max()))
    st.divider()

    col1, col2 = st.columns(2)

    # products per competitor
    with col1:
        st.subheader("Products per Competitor")
        counts = df['source'].value_counts()
        fig, ax = plt.subplots(figsize=(7, 5))
        colors  = [PALETTE[i % len(PALETTE)] for i in range(len(counts))]
        bars = ax.barh(counts.index[::-1], counts.values[::-1], color=colors[::-1])
        for bar, val in zip(bars, counts.values[::-1]):
            ax.text(bar.get_width()+15, bar.get_y()+bar.get_height()/2,
                    f'{val:,}', va='center', fontsize=9)
        ax.set_xlabel('Products')
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)

    # market share pie
    with col2:
        st.subheader("Market Share by Products")
        shares = df['source'].value_counts()
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        wedges, texts, autotexts = ax2.pie(
            shares.values, labels=shares.index,
            autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
            colors=[PALETTE[i % len(PALETTE)] for i in range(len(shares))],
            startangle=90, pctdistance=0.8
        )
        for at in autotexts: at.set_fontsize(8)
        plt.tight_layout()
        st.pyplot(fig2)

    st.divider()
    col3, col4 = st.columns(2)

    # box plot — price spread all competitors
    with col3:
        st.subheader("Price Spread per Competitor (Box Plot)")
        data_per_src = [df[df['source']==s]['price'].dropna().values for s in sources]
        fig3, ax3 = plt.subplots(figsize=(10, 5))
        bp = ax3.boxplot(data_per_src, vert=True, patch_artist=True, notch=False,
                         flierprops=dict(marker='.', markersize=3, alpha=0.3))
        for patch, color in zip(bp['boxes'], PALETTE[:len(sources)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        ax3.set_xticks(range(1, len(sources)+1))
        ax3.set_xticklabels([s.replace(' ','\n') for s in sources], fontsize=8)
        ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_price(x)))
        ax3.set_ylabel('Price (₹)')
        ax3.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig3)
        st.caption("Box = P25–P75, line = median, whiskers = P5–P95, dots = outliers")

    # competitor × segment heatmap
    with col4:
        st.subheader("Competitor × Price Segment Heatmap")
        matrix = df.groupby(['source','price_seg']).size().unstack(fill_value=0)
        matrix = matrix.reindex(columns=PRICE_LABELS, fill_value=0)
        fig4, ax4 = plt.subplots(figsize=(10, 5))
        im = ax4.imshow(matrix.values, cmap='YlOrRd', aspect='auto')
        ax4.set_xticks(range(len(PRICE_LABELS)))
        ax4.set_xticklabels(PRICE_LABELS, rotation=20, fontsize=9)
        ax4.set_yticks(range(len(matrix.index)))
        ax4.set_yticklabels(matrix.index, fontsize=9)
        for i in range(len(matrix.index)):
            for j in range(len(PRICE_LABELS)):
                v = matrix.values[i][j]
                if v > 0:
                    ax4.text(j, i, str(v), ha='center', va='center', fontsize=8,
                             color='white' if v > matrix.values.max()*0.55 else 'black')
        plt.colorbar(im, ax=ax4, shrink=0.8)
        plt.tight_layout()
        st.pyplot(fig4)
        st.caption("Dark red = crowded, white = opportunity")

    st.divider()

    # top keywords
    st.subheader("Keyword Frequency Across All Competitors")
    kw_counts = Counter()
    for t in df['title']:
        for kw in SHAWL_KEYWORDS:
            if kw in t.lower():
                kw_counts[kw] += 1
    kw_df = pd.DataFrame(kw_counts.most_common(20), columns=['keyword','count'])
    kw_df['pct'] = (kw_df['count'] / len(df) * 100).round(1)

    fig5, ax5 = plt.subplots(figsize=(14, 4))
    bars = ax5.bar(kw_df['keyword'], kw_df['pct'],
                   color=['#2196F3' if p > 20 else '#FF9800' if p > 5 else '#4CAF50'
                          for p in kw_df['pct']])
    for bar, val in zip(bars, kw_df['pct']):
        ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                 f'{val:.0f}%', ha='center', fontsize=8)
    ax5.set_ylabel('% of all products')
    ax5.set_xlabel('')
    ax5.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig5)
    st.caption("Blue = very common (>20%), orange = moderate (5–20%), green = rare (<5%)")


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏪 Competitor Deep Dive":
    st.title("🏪 Competitor Deep Dive")

    competitor = st.selectbox("Select Competitor", sources)
    df_c = df[df['source']==competitor]
    color = PALETTE[sources.index(competitor) % len(PALETTE)]

    # KPIs
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric("Products",      f"{len(df_c):,}")
    k2.metric("Avg Price",     fmt_price(df_c['price'].mean()))
    k3.metric("Median",        fmt_price(df_c['price'].median()))
    k4.metric("Lowest",        fmt_price(df_c['price'].min()))
    k5.metric("Highest",       fmt_price(df_c['price'].max()))
    on_sale = df_c['discount_pct'].notna().sum()
    k6.metric("On Sale",       f"{on_sale:,} ({on_sale/len(df_c)*100:.0f}%)")
    st.divider()

    col1, col2 = st.columns(2)

    # price histogram
    with col1:
        st.subheader("Price Distribution")
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(df_c['price'], bins=40, color=color, edgecolor='white', alpha=0.85)
        ax.axvline(df_c['price'].mean(),   color='black',  linewidth=1.5, linestyle='--', label=f"Mean {fmt_price(df_c['price'].mean())}")
        ax.axvline(df_c['price'].median(), color='orange', linewidth=1.5, linestyle='-',  label=f"Median {fmt_price(df_c['price'].median())}")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_price(x)))
        ax.set_xlabel('Price')
        ax.set_ylabel('Products')
        ax.legend(fontsize=9)
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)

    # price percentile table
    with col2:
        st.subheader("Price Percentile Breakdown")
        pcts = [5,10,25,50,75,90,95]
        pct_vals = np.percentile(df_c['price'].dropna(), pcts)
        pct_df = pd.DataFrame({'Percentile': [f'P{p}' for p in pcts],
                               'Price': [fmt_price(v) for v in pct_vals]})
        st.dataframe(pct_df, use_container_width=True, hide_index=True)

        # discount analysis
        if on_sale > 0:
            st.subheader("Discount Analysis")
            disc = df_c['discount_pct'].dropna()
            d1,d2,d3 = st.columns(3)
            d1.metric("Products On Sale",  f"{len(disc):,}")
            d2.metric("Avg Discount",      f"{disc.mean():.1f}%")
            d3.metric("Max Discount",      f"{disc.max():.0f}%")
            fig2, ax2 = plt.subplots(figsize=(6,2.5))
            ax2.hist(disc, bins=20, color='#FF5722', edgecolor='white', alpha=0.8)
            ax2.set_xlabel('Discount %')
            ax2.set_ylabel('Products')
            ax2.spines[['top','right']].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig2)

    st.divider()
    col3, col4 = st.columns(2)

    # price segments
    with col3:
        st.subheader("Price Segments")
        segs = df_c['price_seg'].value_counts().reindex(PRICE_LABELS, fill_value=0)
        fig3, ax3 = plt.subplots(figsize=(7,3.5))
        bars = ax3.bar(segs.index, segs.values, color=[PALETTE[i % len(PALETTE)] for i in range(len(segs))])
        for bar, v in zip(bars, segs.values):
            if v > 0:
                ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                         str(int(v)), ha='center', fontsize=10)
        ax3.set_ylabel('Products')
        ax3.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig3)

    # keywords
    with col4:
        st.subheader(f"Keywords Used by {competitor}")
        kw_c = {}
        for kw in SHAWL_KEYWORDS:
            c = df_c['title'].str.lower().str.contains(kw, na=False).sum()
            if c > 0:
                kw_c[kw] = c
        kw_sorted = sorted(kw_c.items(), key=lambda x: x[1], reverse=True)[:15]
        if kw_sorted:
            fig4, ax4 = plt.subplots(figsize=(7,4))
            kws, vals = zip(*kw_sorted)
            pcts_kw = [v/len(df_c)*100 for v in vals]
            ax4.barh(list(kws)[::-1], list(pcts_kw)[::-1], color=color)
            ax4.set_xlabel('% of products with this keyword')
            ax4.spines[['top','right']].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig4)

    st.divider()
    st.subheader("Top Products by Price")
    show_cols = [c for c in ['title','price','brand','product_type'] if c in df_c.columns]
    st.dataframe(df_c[show_cols].sort_values('price', ascending=False).head(25),
                 use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💰 Price Intelligence":
    st.title("💰 Price Intelligence")
    st.caption("Deep price analysis — spread, percentiles, keyword premiums, and pricing patterns")

    # ── side-by-side box plots ────────────────────────────────────────────────
    st.subheader("Price Distribution — All Competitors Side by Side")
    data_per_src = [df[df['source']==s]['price'].dropna().values for s in sources]
    fig, ax = plt.subplots(figsize=(14, 6))
    bp = ax.boxplot(data_per_src, vert=True, patch_artist=True,
                    flierprops=dict(marker='.', markersize=3, alpha=0.4, color='gray'),
                    medianprops=dict(color='black', linewidth=2))
    for patch, color in zip(bp['boxes'], PALETTE[:len(sources)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.75)
    ax.set_xticks(range(1, len(sources)+1))
    ax.set_xticklabels([s.replace(' ','\n') for s in sources], fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_price(x)))
    ax.set_ylabel('Price (₹)')
    ax.grid(axis='y', alpha=0.3)
    ax.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    st.caption("Black bar = median. Box = middle 50% of products. Dots = outliers.")

    st.divider()

    # ── full percentile table ─────────────────────────────────────────────────
    st.subheader("Price Percentile Table — All Competitors")
    pcts = [5, 10, 25, 50, 75, 90, 95]
    rows = []
    for src in sources:
        prices = df[df['source']==src]['price'].dropna()
        row = {'Competitor': src, 'Products': len(prices)}
        for p in pcts:
            row[f'P{p}'] = fmt_price(np.percentile(prices, p))
        row['Std Dev'] = fmt_price(prices.std())
        rows.append(row)
    pct_table = pd.DataFrame(rows)
    st.dataframe(pct_table, use_container_width=True, hide_index=True)
    st.caption("P50 = median price. P10 = cheapest 10% of products. P90 = top 10% most expensive.")

    st.divider()

    # ── keyword price premium ─────────────────────────────────────────────────
    st.subheader("Keyword Price Premium — Which Words Command Higher Prices?")
    st.caption("Comparing avg price of products WITH vs WITHOUT each keyword")

    kw_impact = keyword_price_impact(df)

    col1, col2 = st.columns([3, 2])

    with col1:
        fig2, ax2 = plt.subplots(figsize=(9, 6))
        colors = ['#4CAF50' if v > 0 else '#F44336' for v in kw_impact['price_premium']]
        bars = ax2.barh(kw_impact['keyword'], kw_impact['price_premium'], color=colors)
        ax2.axvline(0, color='black', linewidth=0.8)
        for bar, val in zip(bars, kw_impact['price_premium']):
            label = fmt_price(abs(val))
            x = bar.get_width()
            ax2.text(x + (200 if x >= 0 else -200), bar.get_y()+bar.get_height()/2,
                     label, va='center', ha='left' if x >= 0 else 'right', fontsize=8)
        ax2.set_xlabel('Price Premium (₹) vs products without this keyword')
        ax2.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2)
        st.caption("Green = this keyword is associated with HIGHER prices. Red = LOWER prices.")

    with col2:
        st.subheader("Premium Ranking")
        display_kw = kw_impact[['keyword','n_products','avg_price_with','price_premium','pct_premium']].copy()
        display_kw.columns = ['Keyword','# Products','Avg Price (with)','₹ Premium','% Premium']
        display_kw['Avg Price (with)'] = display_kw['Avg Price (with)'].apply(fmt_price)
        display_kw['₹ Premium']        = display_kw['₹ Premium'].apply(lambda x: f"+{fmt_price(x)}" if x > 0 else fmt_price(x))
        display_kw['% Premium']        = display_kw['% Premium'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
        st.dataframe(display_kw, use_container_width=True, hide_index=True)

    st.divider()

    # ── price vs title length scatter ─────────────────────────────────────────
    st.subheader("Price vs Title Length — Do Longer Titles Sell at Higher Prices?")
    col3, col4 = st.columns(2)
    with col3:
        fig3, ax3 = plt.subplots(figsize=(7, 4))
        for i, src in enumerate(sources):
            sub = df[df['source']==src]
            ax3.scatter(sub['title_len'], sub['price'], alpha=0.15,
                        s=10, color=PALETTE[i % len(PALETTE)], label=src)
        ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_price(x)))
        ax3.set_xlabel('Title Length (characters)')
        ax3.set_ylabel('Price (₹)')
        ax3.set_ylim(bottom=0, top=df['price'].quantile(0.97))
        ax3.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig3)

    with col4:
        corr = df['title_len'].corr(df['price'])
        st.metric("Correlation: Title Length vs Price", f"{corr:.3f}")
        st.caption(
            "A positive correlation means longer titles tend to have higher prices. "
            "Typically luxury/handmade items have more descriptive titles."
        )

        # avg price by title length bucket
        df['len_bucket'] = pd.cut(df['title_len'], bins=[0,30,50,70,90,200],
                                  labels=['<30','30-50','50-70','70-90','90+'])
        bucket_avg = df.groupby('len_bucket', observed=True)['price'].mean()
        fig4, ax4 = plt.subplots(figsize=(6, 3))
        ax4.bar(bucket_avg.index, bucket_avg.values,
                color=[PALETTE[i % len(PALETTE)] for i in range(len(bucket_avg))])
        ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: fmt_price(x)))
        ax4.set_xlabel('Title Length (chars)')
        ax4.set_ylabel('Avg Price (₹)')
        ax4.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig4)


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔤 Keyword Intelligence":
    st.title("🔤 Keyword Intelligence")
    st.caption("Who uses what keywords — and which keywords matter most")

    # ── competitor × keyword heatmap ─────────────────────────────────────────
    st.subheader("Competitor × Keyword Heatmap")
    st.caption("Cell = % of that competitor's products using this keyword")

    kw_mat = keyword_matrix(df)
    # filter to keywords that appear at least somewhere
    active_kws = [k for k in SHAWL_KEYWORDS if kw_mat[k].max() > 0]
    kw_mat = kw_mat[active_kws]

    fig, ax = plt.subplots(figsize=(16, max(6, len(sources)*0.7)))
    im = ax.imshow(kw_mat.values, cmap='Blues', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks(range(len(active_kws)))
    ax.set_xticklabels(active_kws, rotation=45, ha='right', fontsize=9)
    ax.set_yticks(range(len(sources)))
    ax.set_yticklabels(kw_mat.index, fontsize=9)
    for i in range(len(sources)):
        for j, kw in enumerate(active_kws):
            v = kw_mat.values[i][j]
            ax.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=7,
                    color='white' if v > 50 else 'black')
    cbar = plt.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label('% of products')
    plt.tight_layout()
    st.pyplot(fig)
    st.caption("Dark blue = this competitor heavily uses this keyword. White = barely uses it.")

    st.divider()
    col1, col2 = st.columns(2)

    # ── keyword exclusivity ───────────────────────────────────────────────────
    with col1:
        st.subheader("Keyword Exclusivity")
        st.caption("Keywords used by only 1–2 competitors = differentiation opportunity")

        excl = []
        for kw in active_kws:
            users = (kw_mat[kw] > 5).sum()  # competitors using it in >5% of products
            avg_price = df[df['title'].str.lower().str.contains(kw, na=False)]['price'].mean()
            excl.append({'Keyword': kw, 'Competitors Using': int(users),
                         'Avg Price': fmt_price(avg_price) if not np.isnan(avg_price) else '—'})
        excl_df = pd.DataFrame(excl).sort_values('Competitors Using')
        st.dataframe(excl_df, use_container_width=True, hide_index=True)

    # ── keyword dominance per competitor ─────────────────────────────────────
    with col2:
        st.subheader("Who Dominates Each Keyword?")
        st.caption("For each keyword, which competitor uses it the most?")

        dom = []
        for kw in active_kws:
            col_vals = kw_mat[kw]
            if col_vals.max() > 0:
                dom.append({'Keyword': kw,
                            'Leader': col_vals.idxmax(),
                            'Leader %': f"{col_vals.max():.0f}%",
                            'Market Avg %': f"{col_vals.mean():.1f}%"})
        dom_df = pd.DataFrame(dom)
        st.dataframe(dom_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── keyword co-occurrence ─────────────────────────────────────────────────
    st.subheader("Keyword Co-occurrence Matrix")
    st.caption("Which keywords appear together in the same product titles?")

    core_kws = ['pashmina','kani','sozni','jamawar','embroidered','cashmere',
                'wool','handmade','luxury','stole','shawl','kashmiri']
    co_kws = [k for k in core_kws if k in active_kws]

    co_mat = np.zeros((len(co_kws), len(co_kws)))
    for t in df['title'].str.lower():
        present = [i for i, k in enumerate(co_kws) if k in t]
        for a in present:
            for b in present:
                co_mat[a][b] += 1

    # normalize by diagonal (how often each appears)
    diag = np.diag(co_mat)
    with np.errstate(divide='ignore', invalid='ignore'):
        co_norm = np.where(diag[:, None] > 0, co_mat / diag[:, None] * 100, 0)
    np.fill_diagonal(co_norm, 0)

    fig2, ax2 = plt.subplots(figsize=(10, 8))
    im2 = ax2.imshow(co_norm, cmap='Oranges', vmin=0, vmax=100)
    ax2.set_xticks(range(len(co_kws)))
    ax2.set_xticklabels(co_kws, rotation=45, ha='right', fontsize=9)
    ax2.set_yticks(range(len(co_kws)))
    ax2.set_yticklabels(co_kws, fontsize=9)
    for i in range(len(co_kws)):
        for j in range(len(co_kws)):
            v = co_norm[i][j]
            if v > 0:
                ax2.text(j, i, f'{v:.0f}', ha='center', va='center', fontsize=8,
                         color='white' if v > 60 else 'black')
    plt.colorbar(im2, ax=ax2, shrink=0.8, label='% of row-keyword products that also have col-keyword')
    plt.tight_layout()
    st.pyplot(fig2)
    st.caption("Row 'pashmina' + col 'stole' = % of pashmina products that also say 'stole'")


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "💡 Market Gaps":
    st.title("💡 Market Gaps & Opportunities")

    col1, col2 = st.columns(2)

    # ── price segment competition density ────────────────────────────────────
    with col1:
        st.subheader("Competition Density by Price Segment")
        seg_counts = df['price_seg'].value_counts().reindex(PRICE_LABELS).fillna(0)
        mean_count = seg_counts.mean()
        bar_colors = ['#F44336' if v > mean_count else
                      '#4CAF50' if v < mean_count * 0.4 else '#FF9800'
                      for v in seg_counts.values]
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(seg_counts.index, seg_counts.values, color=bar_colors)
        ax.axhline(mean_count, color='gray', linestyle='--', linewidth=1, label=f'Avg ({mean_count:.0f})')
        for bar, v in zip(bars, seg_counts.values):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
                    int(v), ha='center', fontsize=10)
        ax.set_ylabel('Competitor Products')
        ax.legend(fontsize=9)
        ax.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)
        st.caption("🟢 Green = low competition (enter here) | 🔴 Red = very crowded")

    # ── competition intensity score by segment ───────────────────────────────
    with col2:
        st.subheader("How Many Competitors in Each Segment?")
        comp_by_seg = df.groupby('price_seg', observed=True)['source'].nunique().reindex(PRICE_LABELS).fillna(0)
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        bars2 = ax2.bar(comp_by_seg.index, comp_by_seg.values,
                        color=[PALETTE[i % len(PALETTE)] for i in range(len(comp_by_seg))])
        for bar, v in zip(bars2, comp_by_seg.values):
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05,
                     int(v), ha='center', fontsize=10)
        ax2.set_ylabel('Number of Competitors Present')
        ax2.set_ylim(0, n_src+1)
        ax2.spines[['top','right']].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig2)
        st.caption("Fewer competitors = less price pressure = better margins")

    st.divider()

    # ── fine-grained price gap finder ────────────────────────────────────────
    st.subheader("Price Range Gap Finder")
    bucket_size = st.slider("Bucket size (₹)", 500, 5000, 1000, step=500)
    max_price   = int(df['price'].quantile(0.95))
    buckets     = list(range(0, max_price + bucket_size, bucket_size))
    df2         = df.copy()
    df2['bucket'] = pd.cut(df2['price'], bins=buckets, right=False)
    bucket_counts = df2['bucket'].value_counts().sort_index()
    threshold     = bucket_counts.mean() * 0.25

    fig3, ax3 = plt.subplots(figsize=(14, 4))
    bar_cols = ['#F44336' if v > bucket_counts.mean() else
                '#4CAF50' if v < threshold else '#2196F3'
                for v in bucket_counts.values]
    ax3.bar(range(len(bucket_counts)), bucket_counts.values, color=bar_cols)
    step = max(1, len(bucket_counts)//14)
    ax3.set_xticks(range(0, len(bucket_counts), step))
    ax3.set_xticklabels(
        [f"₹{int(b.left//1000)}K" for b in bucket_counts.index[::step]],
        rotation=45, fontsize=8
    )
    ax3.set_xlabel('Price Range')
    ax3.set_ylabel('Competitor Products')
    ax3.axhline(threshold, color='green', linestyle='--', linewidth=1.2, label='Gap threshold')
    ax3.legend(fontsize=9)
    ax3.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig3)

    gaps = bucket_counts[bucket_counts < threshold]
    if not gaps.empty:
        gap_ranges = [f"₹{int(b.left):,}–₹{int(b.right):,}" for b in gaps.index]
        st.success(f"**{len(gaps)} underserved price ranges found:**  " + " | ".join(gap_ranges[:12]))
    else:
        st.info("No major gaps at this bucket size. Try smaller buckets.")

    st.divider()

    # ── competitor segment matrix (full) ─────────────────────────────────────
    st.subheader("Full Competitor × Segment Matrix")
    cs = competition_scores(df)
    pivot = cs.pivot_table(index='source', columns='price_seg', values='intensity', fill_value=0)
    pivot = pivot.reindex(columns=PRICE_LABELS, fill_value=0)
    fig4, ax4 = plt.subplots(figsize=(12, 5))
    im4 = ax4.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=50)
    ax4.set_xticks(range(len(PRICE_LABELS)))
    ax4.set_xticklabels(PRICE_LABELS, rotation=20, fontsize=9)
    ax4.set_yticks(range(len(pivot.index)))
    ax4.set_yticklabels(pivot.index, fontsize=9)
    for i in range(len(pivot.index)):
        for j in range(len(PRICE_LABELS)):
            v = pivot.values[i][j]
            ax4.text(j, i, f'{v:.0f}%', ha='center', va='center', fontsize=8,
                     color='white' if v > 30 else 'black')
    plt.colorbar(im4, ax=ax4, label="% share of that segment's products")
    plt.tight_layout()
    st.pyplot(fig4)
    st.caption("Red = this competitor dominates this segment. Green = low presence = room for you.")


# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Demand Calendar":
    st.title("📅 Demand Calendar")

    try:
        df_trends = load_trends()
        st.subheader("Pashmina Search Interest Over Time")
        fig, ax = plt.subplots(figsize=(13, 5))
        for i, region in enumerate(df_trends['region'].unique()):
            d = df_trends[df_trends['region']==region]
            ax.plot(d['date'], d['interest'], label=region,
                    linewidth=2, color=PALETTE[i % len(PALETTE)])
        ax.set_xlabel('Date')
        ax.set_ylabel('Search Interest (0–100)')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.spines[['top','right']].set_visible(False)
        plt.xticks(rotation=30)
        plt.tight_layout()
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Trends data unavailable: {e}")

    st.divider()
    st.subheader("📆 Monthly Playbook")

    playbook = {
        'Jan':  ('#F44336','🔥 PEAK',      'Maximum stock, push premium, paid ads on'),
        'Feb':  ('#FF5722','📈 STRONG',     'Maintain inventory, push embroidered & kani'),
        'Mar':  ('#FF9800','📉 SLOWING',    'New design launches, plan spring collection'),
        'Apr':  ('#2196F3','❄️ LOW',        'Photography, listing optimization, rest'),
        'May':  ('#4CAF50','➡️ MODERATE',   'Summer wraps, stoles — test new keywords'),
        'Jun':  ('#4CAF50','➡️ MODERATE',   'Mid-year review, pre-buy raw material'),
        'Jul':  ('#2196F3','❄️ LOW',        'Stock raw material, plan autumn range'),
        'Aug':  ('#FF9800','📈 BUILDING',   'Start listings, launch pre-season campaign'),
        'Sep':  ('#FF9800','📈 GROWING',    'Full stock up, gifting bundles ready'),
        'Oct':  ('#F44336','🔥 PRE-PEAK',   'Aggressive ads, festival offers, full inventory'),
        'Nov':  ('#F44336','🔥 PEAK',       'Maximum stock, push luxury items'),
        'Dec':  ('#F44336','🔥 GIFT PEAK',  'Gift season — bundles, express, premium push'),
    }

    cols = st.columns(4)
    for i, (month, (color, status, tip)) in enumerate(playbook.items()):
        with cols[i % 4]:
            st.markdown(
                f"<div style='border-left:4px solid {color};padding:8px 10px;"
                f"margin:5px 0;border-radius:4px;background:#1e1e1e11'>"
                f"<b>{month}</b> &nbsp;<span style='color:{color};font-weight:600'>{status}</span>"
                f"<br><small style='color:#888'>{tip}</small></div>",
                unsafe_allow_html=True
            )

    st.divider()
    st.subheader("Peak Season Pricing Strategy")
    st.markdown("""
| Period | Action | Why |
|--------|--------|-----|
| Oct–Jan | Raise prices 10–20% | Demand spikes, price sensitivity drops |
| Feb–Mar | Hold price | Strong but fading, compete on value |
| Apr–Jul | Discount 10–15% | Clear slow-movers, drive traffic |
| Aug–Sep | Reset to full price | New season arrivals, customers expect it |
    """)

"""
Advanced competitor scraper for Kashmiri shawl market intelligence.

Anti-detection stack:
  - cloudscraper: bypasses CloudFlare JS challenges automatically
  - 30+ rotating Chrome user agents
  - Per-domain rate limiting (never hit same domain twice too fast)
  - Status-aware retry: 429 → long backoff, 403 → UA rotation, 503 → wait+retry
  - Random jitter on all delays (looks like a human browsing)
  - Proxy rotation support (add proxies to PROXIES list)
  - Selenium stealth (patches navigator.webdriver, WebGL, platform fingerprints)
  - Random viewport sizes per session
  - Header randomization (Accept-Language, Referer, Cache-Control)
"""

import os
import re
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── optional advanced packages (graceful fallback if not installed) ─────────
try:
    import cloudscraper as _cs
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    print("[scraper] cloudscraper not installed — using requests (pip install cloudscraper)")

try:
    from selenium_stealth import stealth as _stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

# ── proxy rotation (add your proxies here) ────────────────────────────────────
# Format: 'http://user:pass@ip:port'  or  'http://ip:port'
PROXIES = []

# ── rotating user agents (30 real Chrome UAs) ────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Linux; Android 12; moto g(60)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

ACCEPT_LANGUAGES = [
    'en-IN,en-GB;q=0.9,en;q=0.8',
    'en-US,en;q=0.9',
    'en-GB,en;q=0.8,en-US;q=0.7',
    'en-IN,en;q=0.9,hi;q=0.7',
    'en-US,en;q=0.9,hi;q=0.8',
]

VIEWPORTS = [(1920,1080), (1366,768), (1440,900), (1536,864), (1280,720)]

# per-domain last-request timestamp for rate limiting
_DOMAIN_LAST_HIT: dict = {}

# ── shawl product filter ──────────────────────────────────────────────────────
SHAWL_INCLUDE = [
    'shawl', 'stole', 'pashmina', 'wrap', 'scarf', 'cashmere',
    'kani', 'sozni', 'jamawar', 'aari', 'tilla', 'hashida', 'jaldaar',
    'namda', 'dorukha', 'shahtoosh',
]
SHAWL_EXCLUDE = [
    'suit', 'jacket', 'kurta', 'trouser', 'pant', 'saree', 'sari',
    'pillow', 'cushion', 'blanket', 'quilt', 'bed sheet', 'bedsheet',
    'bed cover', 'rug', 'carpet', 'wall hanging', 'table', 'bag',
    'cap', 'hat', 'glove', 'sock',
]

def is_shawl(title, product_type=''):
    text = (title + ' ' + (product_type or '')).lower()
    if any(kw in text for kw in SHAWL_EXCLUDE):
        return False
    return any(kw in text for kw in SHAWL_INCLUDE)


# ── core HTTP engine ──────────────────────────────────────────────────────────

def _rate_limit(domain: str, min_gap: float = 2.0):
    """Block until min_gap seconds have passed since the last hit on this domain."""
    now = time.time()
    gap = now - _DOMAIN_LAST_HIT.get(domain, 0)
    if gap < min_gap:
        time.sleep(min_gap - gap + random.uniform(0, 1.0))
    _DOMAIN_LAST_HIT[domain] = time.time()


def _random_headers(referer: str = ''):
    hdrs = {
        'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(ACCEPT_LANGUAGES),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT':             '1',
        'Connection':      'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest':  'document',
        'Sec-Fetch-Mode':  'navigate',
        'Sec-Fetch-Site':  'none',
        'Cache-Control':   random.choice(['max-age=0', 'no-cache']),
    }
    if referer:
        hdrs['Referer'] = referer
    return hdrs


def make_session() -> requests.Session:
    """Create an HTTP session with CloudFlare bypass and anti-detection headers."""
    if HAS_CLOUDSCRAPER:
        sess = _cs.create_scraper(
            browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
        )
    else:
        sess = requests.Session()
    sess.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    sess.headers.update(_random_headers())
    if PROXIES:
        proxy = random.choice(PROXIES)
        sess.proxies = {'http': proxy, 'https': proxy}
    return sess


def fetch(session, url: str, max_retries: int = 3, min_gap: float = 2.0):
    """
    Fetch URL with:
    - per-domain rate limiting
    - 429 → exponential backoff
    - 403 → rotate User-Agent and retry
    - 503 → wait and retry
    - random jitter on all delays
    """
    domain = re.sub(r'^www\.', '', url.split('/')[2])
    for attempt in range(max_retries):
        try:
            _rate_limit(domain, min_gap)
            resp = session.get(url, timeout=20)

            if resp.status_code == 200:
                return resp

            elif resp.status_code == 429:
                wait = (2 ** attempt) * 8 + random.uniform(2, 5)
                print(f"    [429] Rate limited on {domain} — waiting {wait:.0f}s (attempt {attempt+1})")
                time.sleep(wait)

            elif resp.status_code == 403:
                new_ua = random.choice(USER_AGENTS)
                session.headers.update({'User-Agent': new_ua})
                session.headers.update(_random_headers())
                print(f"    [403] Rotating UA on {domain} (attempt {attempt+1})")
                time.sleep(random.uniform(3, 6))

            elif resp.status_code == 503:
                wait = (2 ** attempt) * 4 + random.uniform(1, 3)
                print(f"    [503] Service unavailable on {domain} — waiting {wait:.0f}s")
                time.sleep(wait)

            elif resp.status_code in (301, 302):
                return resp  # let requests handle redirect

            else:
                print(f"    [HTTP {resp.status_code}] {url[:60]}")
                break

        except requests.exceptions.ConnectionError as e:
            wait = (2 ** attempt) * 3 + random.uniform(1, 3)
            print(f"    [ConnErr] {domain} attempt {attempt+1} — retry in {wait:.0f}s")
            time.sleep(wait)
        except requests.exceptions.Timeout:
            print(f"    [Timeout] {url[:60]} attempt {attempt+1}")
            time.sleep(random.uniform(3, 6))
        except Exception as e:
            print(f"    [Error] {e}")
            break

    return None


# ── Selenium stealth driver ───────────────────────────────────────────────────

def make_driver():
    """
    Chrome WebDriver with:
    - headless mode
    - navigator.webdriver patched to undefined
    - selenium-stealth (if installed): patches WebGL, platform, vendor fingerprints
    - random viewport
    - random User-Agent
    """
    w, h = random.choice(VIEWPORTS)
    ua   = random.choice(USER_AGENTS)

    options = Options()
    options.add_argument('--headless=new')
    options.add_argument(f'--window-size={w},{h}')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument(f'--user-agent={ua}')
    options.add_argument(f'--lang={random.choice(["en-US","en-IN","en-GB"])}')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    # patch webdriver detection via JS
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
            window.chrome = {runtime: {}};
        '''
    })

    if HAS_STEALTH:
        _stealth(driver,
            languages=['en-US', 'en'],
            vendor='Google Inc.',
            platform='Win32',
            webgl_vendor='Intel Inc.',
            renderer='Intel Iris OpenGL Engine',
            fix_hairline=True,
        )

    return driver


# ── site definitions ──────────────────────────────────────────────────────────
SHOPIFY_SITES = [
    {'domain': 'kashmirbox.com',         'name': 'Kashmir Box',      'market': 'India'},
    {'domain': 'kashmirloom.com',        'name': 'Kashmir Loom',     'market': 'Global'},
    {'domain': 'purekashmir.com',        'name': 'Pure Kashmir',     'market': 'India'},
    {'domain': 'kashmirvilla.com',       'name': 'Kashmir Villa',    'market': 'India'},
    {'domain': 'kashmkari.com',          'name': 'Kashmkari',        'market': 'India'},
    {'domain': 'shahkaar.com',           'name': 'Shahkaar',         'market': 'Global'},
    {'domain': 'handwoven.aadyam.co.in', 'name': 'Aadyam Handwoven', 'market': 'India'},
    {'domain': 'pashtush.in',            'name': 'Pashtush',         'market': 'India'},
    {'domain': 'kepra.in',               'name': 'Kepra',            'market': 'India'},
    {'domain': 'phamb.com',              'name': 'Phamb',            'market': 'India'},
    {'domain': 'ahujasons.com',          'name': 'Ahuja Sons',       'market': 'India'},
]


# ── scrapers ──────────────────────────────────────────────────────────────────

def scrape_shopify(site: dict) -> list:
    """Shopify /products.json pagination with anti-detection."""
    name    = site['name']
    domain  = site['domain']
    market  = site['market']
    session = make_session()
    products = []
    page = 1

    print(f"  [{name}] Shopify scrape starting...")

    while True:
        url  = f"https://{domain}/products.json?limit=250&page={page}"
        resp = fetch(session, url, min_gap=1.5)

        if resp is None:
            print(f"    [{name}] fetch failed on page {page}, stopping")
            break

        try:
            data = resp.json().get('products', [])
        except Exception:
            break

        if not data:
            break

        for p in data:
            title        = p.get('title', '')
            product_type = p.get('product_type', '')

            if not is_shawl(title, product_type):
                continue

            variant        = p['variants'][0] if p.get('variants') else {}
            price          = variant.get('price')
            original_price = variant.get('compare_at_price')
            image_url      = p['images'][0].get('src') if p.get('images') else None

            products.append({
                'brand':          p.get('vendor', name),
                'title':          title,
                'price':          float(price)          if price          else None,
                'original_price': float(original_price) if original_price else None,
                'product_type':   product_type,
                'image_url':      image_url,
                'source':         name,
                'market':         market,
                'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
            })

        print(f"    [{name}] page {page}: {len(data)} total, {len(products)} shawls so far")
        page += 1

        # rotate UA every 3 pages
        if page % 3 == 0:
            session.headers.update({'User-Agent': random.choice(USER_AGENTS)})

    print(f"  [{name}] done — {len(products)} shawl products")
    return products


def _scrape_kcsshop_product(args):
    url, session = args
    try:
        resp = fetch(session, url, min_gap=0.8)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        title_el = soup.select_one('h1.product_title, h1.entry-title')
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        if not is_shawl(title):
            return None

        price_el = soup.select_one(
            '.price ins .woocommerce-Price-amount bdi, '
            '.price > .woocommerce-Price-amount bdi, '
            '.price .amount bdi'
        )
        orig_el = soup.select_one('.price del .woocommerce-Price-amount bdi')
        img_el  = soup.select_one(
            '.woocommerce-product-gallery__image img, '
            '.wp-post-image, figure img'
        )

        def parse_price(el):
            if not el:
                return None
            raw = el.get_text(strip=True)
            cleaned = ''.join(c for c in raw if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None

        price = parse_price(price_el)
        if price is None:
            return None

        return {
            'brand':          'KCS Shop',
            'title':          title,
            'price':          price,
            'original_price': parse_price(orig_el),
            'product_type':   'Shawl',
            'image_url':      (img_el.get('data-large_image') or img_el.get('src')) if img_el else None,
            'source':         'KCS Shop',
            'market':         'India',
            'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
        }
    except Exception:
        return None


def scrape_kcsshop() -> list:
    """kcsshop.in — WooCommerce sitemap discovery + parallel product scraping."""
    print("  [KCS Shop] sitemap discovery...")

    session       = make_session()
    product_urls  = []

    # try multiple sitemap patterns
    sitemap_patterns = [
        'https://kcsshop.in/wp-sitemap-posts-product-{n}.xml',
        'https://kcsshop.in/sitemap_products_{n}.xml',
    ]

    for pattern in sitemap_patterns:
        found_any = False
        for i in range(1, 15):
            url  = pattern.format(n=i)
            resp = fetch(session, url, min_gap=1.0)
            if not resp or resp.status_code != 200:
                break
            soup = BeautifulSoup(resp.text, 'xml')
            urls = [
                loc.text for loc in soup.find_all('loc')
                if '/product/' in loc.text
                and not any(loc.text.endswith(ext) for ext in ('.jpg','.png','.webp'))
            ]
            if not urls:
                break
            product_urls.extend(urls)
            found_any = True
        if found_any:
            break

    # pre-filter by URL slug
    SLUG_EXCLUDE = ['bed-cover','blanket','rug','carpet','cushion','pillow','cap','glove']
    product_urls = [u for u in product_urls if not any(k in u for k in SLUG_EXCLUDE)]
    product_urls = list(set(product_urls))  # dedup

    print(f"    [KCS Shop] {len(product_urls)} candidate URLs — scraping in parallel...")

    products = []
    sessions = [make_session() for _ in range(8)]

    def _work(i_url):
        url = i_url
        sess = sessions[hash(url) % len(sessions)]
        return _scrape_kcsshop_product((url, sess))

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_work, u): u for u in product_urls}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                products.append(r)

    print(f"  [KCS Shop] done — {len(products)} shawl products")
    return products


def scrape_pashmina_com() -> list:
    """
    pashmina.com — Next.js SPA.
    Strategy 1: intercept XHR/API calls via CDP performance logs (fast, clean JSON)
    Strategy 2: Selenium scroll with stealth (fallback)
    """
    print("  [Pashmina.com] stealth Selenium scrape...")
    products = []

    TARGET_URLS = [
        'https://www.pashmina.com/pashmina-shawl/',
        'https://www.pashmina.com/mens-cashmere-shawl/',
        'https://www.pashmina.com/pashmina-stole/',
    ]

    driver = make_driver()

    try:
        for url in TARGET_URLS:
            try:
                driver.get(url)
                time.sleep(random.uniform(6, 10))  # let JS render

                # scroll to trigger lazy loading
                last_count = 0
                for _ in range(20):
                    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(random.uniform(1.5, 2.5))
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    count = len(soup.select('h3 a[href]'))
                    if count == last_count and count > 0:
                        break
                    last_count = count

                soup       = BeautifulSoup(driver.page_source, 'html.parser')
                title_els  = soup.select('h3 a[href]')
                price_els  = soup.select('p.float-left span, .price-display span, [class*=price] span')
                img_els    = soup.select('div.group img, [class*=product] img')

                for i, (link, price_el) in enumerate(zip(title_els, price_els)):
                    try:
                        p_tag = link.find('p')
                        title = (p_tag.get_text(strip=True) if p_tag else link.get_text(strip=True))
                        if not title or not is_shawl(title):
                            continue

                        raw   = price_el.get_text(strip=True)
                        clean = ''.join(c for c in raw if c.isdigit() or c == '.')
                        price = float(clean) if clean else None
                        if price is None:
                            continue

                        products.append({
                            'brand':          'Pashmina.com',
                            'title':          title,
                            'price':          price,
                            'original_price': None,
                            'product_type':   'Pashmina',
                            'image_url':      img_els[i].get('src') if i < len(img_els) else None,
                            'source':         'Pashmina.com',
                            'market':         'Global',
                            'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
                        })
                    except Exception:
                        continue

            except Exception as e:
                print(f"    [Pashmina.com] error on {url}: {e}")
    finally:
        driver.quit()

    print(f"  [Pashmina.com] done — {len(products)} shawl products")
    return products


# ── orchestrator ──────────────────────────────────────────────────────────────

def scrape_all() -> pd.DataFrame:
    print(f"\n{'='*60}")
    print(f"  Scrape started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Anti-detection: cloudscraper={'ON' if HAS_CLOUDSCRAPER else 'OFF'}, "
          f"selenium-stealth={'ON' if HAS_STEALTH else 'OFF'}, "
          f"proxies={len(PROXIES)}")
    print(f"{'='*60}\n")

    all_products = []

    for site in SHOPIFY_SITES:
        try:
            all_products.extend(scrape_shopify(site))
        except Exception as e:
            print(f"  [FAIL] {site['name']}: {e}")

    try:
        all_products.extend(scrape_kcsshop())
    except Exception as e:
        print(f"  [FAIL] KCS Shop: {e}")

    try:
        all_products.extend(scrape_pashmina_com())
    except Exception as e:
        print(f"  [FAIL] Pashmina.com: {e}")

    df = pd.DataFrame(all_products)
    df = df.dropna(subset=['title', 'price'])
    df = df.drop_duplicates(subset=['title', 'source'])
    df = df.reset_index(drop=True)
    return df


# ── standalone run ────────────────────────────────────────────────────────────
if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    df = scrape_all()

    print(f"\n{'='*60}")
    print(f"  Total shawl products scraped: {len(df)}")
    print(f"\n{df['source'].value_counts().to_string()}")

    out = os.path.join(ROOT, 'data', 'competitor_products.csv')
    df.to_csv(out, index=False)
    print(f"\n  Saved: {out}")

    cols = ['brand', 'title', 'price', 'source', 'market', 'scraped_date']
    df[cols].to_csv(os.path.join(ROOT, 'data', 'master_dataset.csv'), index=False)
    print(f"  Master dataset: {len(df)} products")
    print(f"\n  Scrape complete: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

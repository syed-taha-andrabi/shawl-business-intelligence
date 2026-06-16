import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

SHAWL_INCLUDE = [
    'shawl', 'stole', 'pashmina', 'wrap', 'scarf', 'cashmere',
    'kani', 'sozni', 'jamawar', 'aari', 'tilla', 'hashida', 'jaldaar',
    'namda', 'shahtoosh', 'dorukha'
]

SHAWL_EXCLUDE = [
    'suit', 'jacket', 'kurta', 'trouser', 'pant', 'dress',
    'saree', 'sari', 'dupatta', 'pillow', 'cushion', 'blanket',
    'quilt', 'bed sheet', 'bedsheet', 'bed-cover', 'bed cover',
    'rug', 'carpet', 'wall hanging', 'cushion cover', 'table',
    'bag', 'cap', 'hat', 'glove', 'sock'
]

SHOPIFY_SITES = [
    {'domain': 'kashmirbox.com',         'name': 'Kashmir Box',       'market': 'India'},
    {'domain': 'kashmirloom.com',        'name': 'Kashmir Loom',      'market': 'Global'},
    {'domain': 'purekashmir.com',        'name': 'Pure Kashmir',      'market': 'India'},
    {'domain': 'kashmirvilla.com',       'name': 'Kashmir Villa',     'market': 'India'},
    {'domain': 'kashmkari.com',          'name': 'Kashmkari',         'market': 'India'},
    {'domain': 'shahkaar.com',           'name': 'Shahkaar',          'market': 'Global'},
    {'domain': 'handwoven.aadyam.co.in', 'name': 'Aadyam Handwoven',  'market': 'India'},
    {'domain': 'pashtush.in',            'name': 'Pashtush',          'market': 'India'},
    {'domain': 'kepra.in',               'name': 'Kepra',             'market': 'India'},
    {'domain': 'phamb.com',              'name': 'Phamb',             'market': 'India'},
    {'domain': 'ahujasons.com',          'name': 'Ahuja Sons',        'market': 'India'},
]


def is_shawl(title, product_type=''):
    text = (title + ' ' + (product_type or '')).lower()
    if any(kw in text for kw in SHAWL_EXCLUDE):
        return False
    return any(kw in text for kw in SHAWL_INCLUDE)


def scrape_shopify(site):
    domain = site['domain']
    name = site['name']
    market = site['market']
    products = []
    page = 1

    print(f"  Scraping {name} (Shopify)...")

    while True:
        url = f"https://{domain}/products.json?limit=250&page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                break
            data = resp.json().get('products', [])
            if not data:
                break

            for p in data:
                title = p.get('title', '')
                product_type = p.get('product_type', '')

                if not is_shawl(title, product_type):
                    continue

                variant = p['variants'][0] if p.get('variants') else {}
                price = variant.get('price')
                original_price = variant.get('compare_at_price')

                image_url = None
                if p.get('images'):
                    image_url = p['images'][0].get('src')

                products.append({
                    'brand':          p.get('vendor', name),
                    'title':          title,
                    'price':          float(price) if price else None,
                    'original_price': float(original_price) if original_price else None,
                    'product_type':   product_type,
                    'image_url':      image_url,
                    'source':         name,
                    'market':         market,
                    'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
                })

            page += 1
            time.sleep(1.5)

        except Exception as e:
            print(f"    Error on {name} page {page}: {e}")
            break

    print(f"    Found {len(products)} shawl products")
    return products


def _get_kcsshop_product(url):
    """Scrape a single kcsshop.in product page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')

        title_el = soup.select_one('h1.product_title, h1.entry-title')
        if not title_el:
            return None
        title = title_el.get_text(strip=True)

        if not is_shawl(title):
            return None

        price_el = soup.select_one('.price ins .woocommerce-Price-amount bdi, '
                                   '.price > .woocommerce-Price-amount bdi, '
                                   '.price .amount bdi')
        orig_el = soup.select_one('.price del .woocommerce-Price-amount bdi')
        img_el = soup.select_one('.woocommerce-product-gallery__image img, '
                                 '.wp-post-image, figure.woocommerce-product-gallery__wrapper img')

        def parse_price(el):
            if not el:
                return None
            raw = el.get_text(strip=True)
            cleaned = ''.join(c for c in raw if c.isdigit() or c == '.')
            return float(cleaned) if cleaned else None

        price = parse_price(price_el)
        original_price = parse_price(orig_el)
        image_url = img_el.get('data-large_image') or img_el.get('src') if img_el else None

        if price is None:
            return None

        return {
            'brand':          'KCS Shop',
            'title':          title,
            'price':          price,
            'original_price': original_price,
            'product_type':   'Shawl',
            'image_url':      image_url,
            'source':         'KCS Shop',
            'market':         'India',
            'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
        }
    except Exception:
        return None


def scrape_kcsshop():
    """kcsshop.in — WooCommerce sitemap → parallel product page scraping."""
    print("  Scraping KCS Shop (WooCommerce sitemap)...")

    # collect all product URLs from sitemap
    product_urls = []
    for i in range(1, 10):
        try:
            r = requests.get(f'https://kcsshop.in/wp-sitemap-posts-product-{i}.xml',
                             headers=HEADERS, timeout=20)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, 'xml')
            urls = [
                loc.text for loc in soup.find_all('loc')
                if '/product/' in loc.text
                and not loc.text.endswith(('.jpg', '.png', '.webp'))
            ]
            if not urls:
                break
            product_urls.extend(urls)
        except Exception:
            break

    # pre-filter by URL slug to skip obvious non-shawl items
    product_urls = [
        u for u in product_urls
        if not any(k in u for k in ['bed-cover', 'blanket', 'rug', 'carpet', 'cushion', 'pillow'])
    ]

    print(f"    {len(product_urls)} candidate URLs, scraping in parallel...")

    products = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_get_kcsshop_product, url): url for url in product_urls}
        for future in as_completed(futures):
            result = future.result()
            if result:
                products.append(result)

    print(f"    Found {len(products)} shawl products")
    return products


def _selenium_driver():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)


def scrape_pashmina_com():
    """pashmina.com — Next.js SPA, Selenium scroll to load all products."""
    print("  Scraping Pashmina.com (Selenium)...")
    products = []

    SHAWL_URLS = [
        'https://www.pashmina.com/pashmina-shawl/',
        'https://www.pashmina.com/mens-cashmere-shawl/',
        'https://www.pashmina.com/pashmina-stole/',
    ]

    driver = _selenium_driver()
    try:
        for base_url in SHAWL_URLS:
            try:
                driver.get(base_url)
                time.sleep(8)

                # scroll repeatedly to trigger lazy loading
                last_count = 0
                for _ in range(15):
                    driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    current_count = len(soup.select('h3 a[href]'))
                    if current_count == last_count:
                        break
                    last_count = current_count

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                title_links = soup.select('h3 a[href]')
                price_spans = soup.select('p.float-left span, .price-display span')
                # image is the sibling <a> wrapping the <img> near each product card
                img_tags = soup.select('div.group img, [class*=product] img')

                for i, (link, price_el) in enumerate(zip(title_links, price_spans)):
                    try:
                        title_p = link.find('p')
                        title = (title_p.get_text(strip=True) if title_p
                                 else link.get_text(strip=True))

                        if not title or not is_shawl(title):
                            continue

                        raw_price = price_el.get_text(strip=True)
                        cleaned = ''.join(c for c in raw_price if c.isdigit() or c == '.')
                        price = float(cleaned) if cleaned else None

                        if price is None:
                            continue

                        image_url = img_tags[i].get('src') if i < len(img_tags) else None

                        products.append({
                            'brand':          'Pashmina.com',
                            'title':          title,
                            'price':          price,
                            'original_price': None,
                            'product_type':   'Pashmina',
                            'image_url':      image_url,
                            'source':         'Pashmina.com',
                            'market':         'Global',
                            'scraped_date':   datetime.now().strftime('%Y-%m-%d'),
                        })
                    except Exception:
                        continue

            except Exception as e:
                print(f"    Error on {base_url}: {e}")
    finally:
        driver.quit()

    print(f"    Found {len(products)} shawl products")
    return products


def scrape_all():
    all_products = []

    for site in SHOPIFY_SITES:
        try:
            all_products.extend(scrape_shopify(site))
        except Exception as e:
            print(f"  Failed {site['name']}: {e}")

    try:
        all_products.extend(scrape_kcsshop())
    except Exception as e:
        print(f"  Failed KCS Shop: {e}")

    try:
        all_products.extend(scrape_pashmina_com())
    except Exception as e:
        print(f"  Failed Pashmina.com: {e}")

    df = pd.DataFrame(all_products)
    df = df.dropna(subset=['title', 'price'])
    df = df.drop_duplicates(subset=['title', 'source'])
    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    print(f"Scraping started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    df = scrape_all()

    print(f"\nTotal shawl products scraped: {len(df)}")
    print(df['source'].value_counts().to_string())

    df.to_csv('data/competitor_products.csv', index=False)
    print("\nSaved: data/competitor_products.csv")

    cols = ['brand', 'title', 'price', 'source', 'market', 'scraped_date']
    master = df[cols].copy()
    master.to_csv('data/master_dataset.csv', index=False)
    print(f"Master dataset updated: {len(master)} products")
    print(f"\nScraping complete: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

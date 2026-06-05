import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(options=options)
    return driver

def scrape_amazon_ae():
    print("Scraping Amazon.ae...")
    driver = get_driver()
    all_products = []

    for page in range(1, 4):
        url = f"https://www.amazon.ae/s?k=kashmiri+pashmina+shawl&page={page}"
        driver.get(url)
        time.sleep(4)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.find_all('div', {'data-component-type': 's-search-result'})

        for item in listings:
            try:
                brand = item.find('span', class_='a-size-base-plus')
                title = item.find('span', attrs={'class': None})
                price = item.find('span', class_='a-price-whole')

                if price:
                    all_products.append({
                        'brand': brand.text.strip() if brand else None,
                        'title': title.text.strip() if title else None,
                        'price': float(price.text.replace(',', '').replace('.', '').strip()),
                        'source': 'Amazon.ae',
                        'market': 'UAE',
                        'scraped_date': datetime.now().strftime('%Y-%m-%d')
                    })
            except:
                continue

        print(f"Page {page} done - {len(all_products)} products so far")
        time.sleep(3)

    driver.quit()
    df = pd.DataFrame(all_products)
    print(f"Total scraped: {len(df)}")
    print(df.head())
    return df

def scrape_amazon_in():
    print("Scraping Amazon.in...")
    driver = get_driver()
    all_products = []

    for page in range(1, 4):
        url = f"https://www.amazon.in/s?k=kashmiri+pashmina+shawl&page={page}"
        driver.get(url)
        time.sleep(4)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        listings = soup.find_all('div', {'data-component-type': 's-search-result'})

        for item in listings:
            try:
                brand = item.find('span', class_='a-size-base-plus')
                title = item.find('span', attrs={'class': None})
                price = item.find('span', class_='a-price-whole')

                if price:
                    all_products.append({
                        'brand': brand.text.strip() if brand else None,
                        'title': title.text.strip() if title else None,
                        'price': float(price.text.replace(',', '').replace('.', '').strip()),
                        'source': 'Amazon.in',
                        'market': 'India',
                        'scraped_date': datetime.now().strftime('%Y-%m-%d')
                    })
            except:
                continue

        print(f"Page {page} done - {len(all_products)} products so far")
        time.sleep(3)

    driver.quit()
    df = pd.DataFrame(all_products)
    print(f"Total scraped: {len(df)}")
    print(df.head())
    return df

def combine_all_data():
    print("Combining all data...")

    df_ae = pd.read_csv('data/amazon_ae_auto.csv')
    df_in = pd.read_csv('data/amazon_in_auto.csv')
    df_etsy = pd.read_csv('data/etsy_clean.csv')

    df_etsy['source'] = 'Etsy'
    df_etsy['market'] = 'Global'
    df_etsy['scraped_date'] = datetime.now().strftime('%Y-%m-%d')
    df_etsy = df_etsy.rename(columns={'sale_price': 'price', 'shop': 'brand'})

    cols = ['brand', 'title', 'price', 'source', 'market', 'scraped_date']

    df_master = pd.concat([
        df_ae[cols],
        df_in[cols],
        df_etsy[cols]
    ], ignore_index=True)

    df_master.to_csv('data/master_dataset.csv', index=False)
    print(f"Master dataset updated: {len(df_master)} total products")
    print(df_master['source'].value_counts())
    return df_master

if __name__ == "__main__":
    # scrape all platforms
    df_amazon_ae = scrape_amazon_ae()
    df_amazon_ae.to_csv('data/amazon_ae_auto.csv', index=False)
    print("Amazon.ae saved!")

    df_amazon_in = scrape_amazon_in()
    df_amazon_in.to_csv('data/amazon_in_auto.csv', index=False)
    print("Amazon.in saved!")

    # combine all data
    combine_all_data()

    # auto push to github
    import subprocess
    subprocess.run(['git', 'add', '.'], cwd='/home/syedtaha/shawl-business-intelligence')
    subprocess.run(['git', 'commit', '-m', f'Auto update: {datetime.now().strftime("%Y-%m-%d")}'],
                   cwd='/home/syedtaha/shawl-business-intelligence')
    subprocess.run(['git', 'push'], cwd='/home/syedtaha/shawl-business-intelligence')
    print("GitHub updated!")
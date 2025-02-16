import csv
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_product_urls(collection_url, max_pages=30):
    """
    Crawl the collection pages using pagination until no more new products
    are found or the maximum page limit is reached.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}
    product_urls = set()
    for page in range(1, max_pages + 1):
        url = f"{collection_url}?page={page}"
        print(f"Scraping product links from: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to load page: {url}")
            break

        soup = BeautifulSoup(response.text, "html.parser")
        links_found = False
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.startswith("/en/products/"):
                full_url = "https://levi.co.th" + href
                if full_url not in product_urls:
                    product_urls.add(full_url)
                    links_found = True
        # If no new products were found on this page, assume we've reached the end.
        if not links_found:
            break
    return list(product_urls)

def scrape_product_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0)"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to load page: {url}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    
    # 1. Extract Product Name from <div class="product__title small-hide"><h1>...</h1></div>
    product_name = "N/A"
    title_container = soup.find("div", class_="product__title small-hide")
    if title_container:
        h1_tag = title_container.find("h1")
        if h1_tag:
            product_name = h1_tag.get_text(strip=True)
    
    # 2. Extract Product Description from <div class="desc-left"> → <div class="full-desc">
    description = "N/A"
    desc_container = soup.find("div", class_="desc-left")
    if desc_container:
        full_desc = desc_container.find("div", class_="full-desc")
        if full_desc:
            description = full_desc.get_text(separator="\n", strip=True)
    
    # 3 & 4. Extract the two lists based on h2 headings with class "desc-title"
    how_it_fits_list = []
    composition_care_list = []
    h2_elements = soup.find_all("h2", class_="desc-title")
    for h2 in h2_elements:
        title_text = h2.get_text(strip=True)
        rich_div = h2.find_next_sibling("div", class_="metafield-rich_text_field")
        if rich_div:
            li_elements = rich_div.find_all("li")
            items = [li.get_text(strip=True) for li in li_elements]
            if title_text.lower() == "how it fits":
                how_it_fits_list = items
            elif "composition" in title_text.lower():
                composition_care_list = items

    # 5. Extract Sale Price from the <div class="price__sale"> element.
    sale_price = "N/A"
    price_sale_div = soup.find("div", class_="price__sale")
    if price_sale_div:
        sale_span = price_sale_div.find("span", class_=lambda x: x and "price-item--sale" in x)
        if sale_span:
            sale_price = sale_span.get_text(strip=True)
    
    # 6. Extract Color Options.
    colors = []
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # Scroll down to ensure dynamic content loads.
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
        # Wait for the swatch elements to appear.
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'swatch-view-item')]")))
    
        # Attempt to extract the color text from the <p> tag inside swatch options.
        color_elements = driver.find_elements(By.XPATH, "//li[contains(@class, 'swatch-view-item')]//div[contains(@class, 'swatch-img-text')]/p")
        for el in color_elements:
            text = el.text.strip()
            if text and text not in colors:
                colors.append(text)
    
        # Fallback: if no text found, try using the data-value attribute.
        if not colors:
            swatch_divs = driver.find_elements(By.XPATH, "//li[contains(@class, 'swatch-view-item')]//div[contains(@class, 'swatch-custom-image')]")
            for div in swatch_divs:
                data_value = div.get_attribute("data-value")
                if data_value and data_value not in colors:
                    colors.append(data_value)
    except Exception as e:
        print("Error extracting colors with Selenium:", e)
    finally:
        driver.quit()

    
    # 7. Extract Images.
    images = []
    image_elements = soup.find_all("li", class_="thumbnail-list__item")
    for element in image_elements:
        img_tag = element.find("img")
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            if img_tag.get("srcset"):
                srcset = img_tag["srcset"].split(", ")
                last_src = srcset[-1].split(" ")[0]
                if last_src:
                    image_url = "https:" + last_src if last_src.startswith("//") else last_src
            images.append(image_url)
    # Fallback: if no images were found using the list items, look for any product image.
    if not images:
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and "/cdn/shop/files/" in src:
                if src.startswith("//"):
                    src = "https:" + src
                images.append(src)
    
    return {
        "product_name": product_name,
        "description": description,
        "how_it_fits": how_it_fits_list,
        "composition_care": composition_care_list,
        "sale_price": sale_price,
        "color": colors,
        "images": images
    }

def save_to_csv(data, filename="products.csv"):
    # Drop the URL column from CSV output.
    fieldnames = ["product_name", "description", "how_it_fits", "composition_care", "sale_price", "color", "images"]
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            row["how_it_fits"] = "; ".join(row["how_it_fits"])
            row["composition_care"] = "; ".join(row["composition_care"])
            row["images"] = "; ".join(row["images"])
            writer.writerow(row)
    print(f"Saved {len(data)} records to {filename}")

if __name__ == "__main__":
    # Define the collection page URL – adjust if needed.
    collection_url = "https://levi.co.th/en/collections/all"
    product_urls = get_product_urls(collection_url)
    print(f"Found {len(product_urls)} product URLs.")

    results = []
    for url in product_urls:
        print(f"Scraping: {url}")
        result = scrape_product_data(url)
        if result:
            results.append(result)
    
    if results:
        save_to_csv(results)

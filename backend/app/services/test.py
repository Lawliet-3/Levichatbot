from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup Chrome Options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize WebDriver
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Open the product page
url = "https://levi.co.th/en/products/levis-mens-501-original-jeans-005011485"
driver.get(url)

# Wait for the page to load
wait = WebDriverWait(driver, 10)

# Try clicking the "Read More" button if it exists
try:
    read_more_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.read-more-button"))  # Update selector if needed
    )
    read_more_button.click()
    print("Clicked 'Read More' button!")
except:
    print("No 'Read More' button found.")

# Extract the full product description after clicking "Read More"
try:
    description_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-description"))  # Update selector if needed
    )
    product_description = description_element.text.strip()
except:
    product_description = "Description not found."

print("Product Description:", product_description)

# Close the browser
driver.quit()

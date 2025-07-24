from cmath import log
from bs4 import BeautifulSoup
import send_different_requests
import data_store 
import bot_functions 
import time 
import source_code_downloader
import browser_functions
import re
import pandas as pd
import json 
import os
import pyautogui 
from dotenv import load_dotenv
# from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError 
from playwright.async_api import async_playwright   
import asyncio

def compare_prices(old_price, new_price):
    """
    Compares two prices (from Excel and scraped value).
    Converts both to float if possible, handling strings with currency symbols.
    Returns True if prices are different, otherwise False.
    """
    def extract_float(price):
        # If already a float or int, return as float
        if isinstance(price, (float, int)):
            return float(price)
        # If not a string, return None
        if not isinstance(price, str):
            return None
        # Try to extract numeric value from string
        nums = re.findall(r'\d+\.\d+|\d+', price)
        if nums:
            return float(nums[0])
        return None

    # Handle "Price not mentioned" or similar
    if isinstance(old_price, str) and "price not mentioned" in old_price.lower():
        new_price_float = extract_float(new_price)
        return new_price_float is not None

    old_price_float = extract_float(old_price)
    new_price_float = extract_float(new_price)

    # print(f"Old price: {old_price_float}, New price: {new_price_float}")

    if old_price_float is not None and new_price_float is not None:
        return old_price_float != new_price_float
    else:
        return None
        # raise ValueError("Invalid price format") 

def extract_asin(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Regex pattern for ASIN (typically 10-character alphanumeric starting with B)
    asin_pattern = r'\bB0[A-Z0-9]{8}\b'

    # Step 1: Search tags with "ASIN" in text
    for tag in soup.find_all(string=re.compile(r'ASIN', re.IGNORECASE)):
        possible_asins = re.findall(asin_pattern, tag)
        if possible_asins:
            return possible_asins[0]

    # Step 2: Search attributes that contain "ASIN"
    for tag in soup.find_all(True):  # all tags
        for attr, val in tag.attrs.items():
            if isinstance(val, str) and 'asin' in attr.lower():
                match = re.search(asin_pattern, val)
                if match:
                    return match.group(0)
            elif isinstance(val, list):
                for v in val:
                    if 'asin' in str(v).lower():
                        match = re.search(asin_pattern, str(v))
                        if match:
                            return match.group(0)

    # Step 3: General fallback: look anywhere in the HTML for a matching ASIN pattern
    match = re.search(asin_pattern, soup.get_text())
    if match:
        return match.group(0)
    
    else: 
        return 'No ASIN found'

def extract_product_details(soup):
    """
    Extracts product details from the soup object and returns them as a clean formatted string

    Args:
        soup: BeautifulSoup object containing the HTML

    Returns:
        str: Clean formatted string containing product details or 'No details found'
    """
    # Find the div containing product details
    product_div = soup.find("div", class_="detail-bullets-wrapper")
    if not product_div:
        return "No details found"

    # Find h2, h3, or h4 tag with 'Product details'
    heading = product_div.find(["h2", "h3", "h4"], string=lambda text: text and "Product details" in text)
    if not heading:
        return "No details found"

    # Find the unordered list inside the div
    details_list = product_div.find("ul", class_="detail-bullet-list")
    if not details_list:
        return "No details found"

    # Initialize empty list to store formatted details
    formatted_details = []

    # Iterate over each list item
    for li in details_list.find_all("li"):
        bold_text = li.find("span", class_="a-text-bold")
        value_span = li.find("span", class_=False)  # Value is in a span without class

        if bold_text and value_span:
            # Clean and format the key-value pair
            key = bold_text.get_text(strip=True).replace(':', '').strip()
            value = value_span.get_text(strip=True).strip()

            # Clean the strings
            key = clean_text(key)
            value = clean_text(value)

            if key and value:  # Only add if both key and value are non-empty
                formatted_details.append(f"{key}: {value}")

    # If no details were found, return the default message
    if not formatted_details:
        return "No details found"

    # Join details with a separator and clean the final string
    result = " | ".join(formatted_details)
    return clean_text(result)

def clean_text(text):
    """
    Clean text by removing special characters and normalizing whitespace

    Args:
        text: String to clean

    Returns:
        str: Cleaned string
    """
    if not text:
        return ""

    # Replace unicode special characters and normalize whitespace
    cleaned = text.encode('ascii', 'ignore').decode('ascii')  # Remove non-ASCII chars
    cleaned = ' '.join(cleaned.split())  # Normalize whitespace
    cleaned = cleaned.strip()  # Remove leading/trailing whitespace

    # Remove any remaining special characters except basic punctuation
    cleaned = ''.join(char for char in cleaned
                     if char.isalnum() or char.isspace()
                     or char in '.,:-()[]/')

    return cleaned

def scrap_product_data(html_content,url):

    """
    Extracts specific information from an Amazon product page HTML content.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Extract Product Name
    product_name = soup.find('h1', id='title')
    product_name = product_name.find('span', id='productTitle').get_text(strip=True) if product_name else ''

    # Extract Product Reviews
    product_ratings = soup.find('span', id='acrPopover')
    product_ratings = product_ratings['title'] if product_ratings else '' 

    total_reviews = soup.find('span', id='acrCustomerReviewText')
    total_reviews = total_reviews.get_text(strip=True) if total_reviews else ''


    # redesign the logic for scraping the bought rate ... 

    # Extract Bought Rate
    # bought_rate = soup.find('span', id='social-proofing-faceout-title-tk_bought')
    # bought_rate = bought_rate.get_text(strip=True) if bought_rate else ''


    # ======================================================================
    # SCRAP PRODUCT OVERVIEW

    overview_div = soup.find('div', {'id': 'productOverview_feature_div'})
    if not overview_div:
        product_overview = 'No Product Overview found'
    
    else:

        rows = overview_div.find_all('tr')
        overview_data = []

        for row in rows:
            key = row.find('span', class_='a-size-base a-text-bold')
            value = row.find('span', class_='a-size-base po-break-word')
            if key and value:
                overview_data.append(f"{key.text.strip()}: {value.text.strip()}")

        product_overview = ', '.join(overview_data)

    # ======================================================================

    price = ''
    price_container = soup.find_all('span', 
                              class_=['a-price', 'a-text-price', 'a-size-medium', 'apexPriceToPay','reinventPricePriceToPayMargin','priceToPay'])
    
    try:
        price_container = price_container[0] 
        if price_container:
            # Find the nested span with class a-offscreen
            price_span = price_container.find('span', class_='a-offscreen')
            if price_span:
                price = price_span.get_text(strip=True)

    except IndexError:
        price = 'No Price mentioned'

    # Extract Price
    # print("the price is ",price)

    # Extract Product Description
    about_this_item = None
    for header_tag in soup.find_all(['h2', 'h3', 'h4']):
        if 'About this item' in header_tag.get_text():
            parent_div = header_tag.find_parent('div')
            if parent_div:
                bullet_points = parent_div.find_all('li')
                about_this_item = ' '.join(bp.get_text(strip=True) for bp in bullet_points)
            break

    # Extract Brand Name
    brand_name = None
    for a_tag in soup.find_all('a'):
        if '/stores/' in a_tag.get('href', ''):
            brand_name = a_tag.get_text(strip=True).replace('Visit the ', '').replace(' Store', '')
            break

    # Product details
    # Product information ...
    # image urls ...

    # Extract Product Information from Table
    product_info = None
    for heading in soup.find_all(['h2', 'h3', 'h4']):
        if 'Product information' in heading.get_text():

            parent_div = heading.find_parent('div')
            if parent_div:
                table = parent_div.find('table')
                if table:
                    info_list = []
                    for row in table.find_all('tr'):
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            info_list.append(f"{th.get_text(strip=True)}: {td.get_text(strip=True)}")
                    product_info = ' | '.join(info_list)
            break
    
    asin_number = extract_asin(html_content)
    return {
        'Product URL' : url,
        'Product name': product_name,
        'Price': price,
        'Brand Name': brand_name,
        'ASIN': asin_number,
        'About this item': about_this_item,
        'Product Information' : product_info,
        'Product Overview' : product_overview,
        'Product Details': extract_product_details(soup),
        'Product Ratings': product_ratings,
        'Total Reviews': total_reviews,
        # 'Bought Rate': bought_rate,
        'Product Images': extract_product_images(soup)
    }

def scrap_product_price_(html_content):

    """
    This function is used to fetch the price only from the amazon product page ...
    """

    soup = BeautifulSoup(html_content, 'html.parser')

    price = ''
    price_container = soup.find_all('span', 
                              class_=['a-price', 'a-text-price', 'a-size-medium', 'apexPriceToPay','reinventPricePriceToPayMargin','priceToPay'])
    
    try:
        price_container = price_container[0] 
        if price_container:
            # Find the nested span with class a-offscreen
            price_span = price_container.find('span', class_='a-offscreen')
            if price_span:
                price = price_span.get_text(strip=True)

    except IndexError:
        price = 'No Price mentioned'

    return price

def convert_file_to_dataframe(file_path):
    """
    Reads an Excel file and extracts Product URL, Price, and Product Name columns into lists
    
    Args:
        file_path (str): Path to the Excel file
        
    Returns:
        tuple: Three lists containing Product URLs, Prices, and Product Names
    """
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)
        
        # Extract columns into lists
        product_urls = df['Product URL'].tolist() if 'Product URL' in df.columns else []
        prices = df['Price'].tolist() if 'Price' in df.columns else []
        product_names = df['Product name'].tolist() if 'Product name' in df.columns else []
        
        # Remove any NaN values and convert to strings
        product_urls = [str(url).strip() for url in product_urls if pd.notna(url)]
        prices = [str(price).strip() for price in prices if pd.notna(price)]
        product_names = [str(name).strip() for name in product_names if pd.notna(name)]
        
        print(f"Extracted {len(product_urls)} products from the Excel file")
        return product_urls, prices, product_names
        
    except FileNotFoundError:
        print(f"Error: File {file_path} not found")
        return [], [], []
    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        return [], [], []

def update_new_price(old_prices_list,new_price,index):

    """
    This function is used to update the new price ... 
    it adds the new value in the list ... 
    """

    new_prices_list = old_prices_list[index] = new_price 
    return new_prices_list

def extract_product_images(soup):
    """
    Extracts product image URLs from Amazon product page

    Args:
        soup: BeautifulSoup object containing the HTML

    Returns:
        str: Comma-separated string of up to 5 image URLs or empty string if none found
    """
    # Find all img tags
    img_tags = soup.find_all('img')

    # Initialize list to store valid Amazon image URLs
    image_urls = []

    # Extract valid Amazon media URLs
    for img in img_tags:
        src = img.get('src', '')
        # Check if it's an Amazon media image URL
        if 'https://m.media-amazon.com/images/S/' in src:
            # Clean the URL and add to list
            clean_url = src.split('?')[0]  # Remove query parameters
            if clean_url not in image_urls:  # Avoid duplicates
                image_urls.append(clean_url)

    # Take only first 5 unique URLs
    image_urls = image_urls[:8]

    # If no images found, return empty string
    if not image_urls:
        return ""

    # Join URLs with comma and space
    return " , ".join(image_urls)

def read_urls_from_file(file_path):
    """
    Reads URLs from a file and returns them as a list
    
    Args:
        file_path (str): Path to the file containing URLs
        
    Returns:
        list: List of URLs, or empty list if file not found or empty
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read lines and strip whitespace, filter out empty lines
            urls = [line.strip() for line in file if line.strip()]
        return urls
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return []

def scraping_robot_():
    """
    This function is used to control the entire web scraping process
    """
    # Read URLs from file
    urls = read_urls_from_file('amazon-product-links.txt')
    
    if not urls:
        print("No URLs found to process.")
        return
        
    for url in urls:
        response_vector = send_different_requests.execute_different_functions(url)
        
        if response_vector is not None:
            data = scrap_product_data(response_vector[0].text,url) 
            # print(f"The scraped data is {data}")

        with open("amazon_source_code.txt","w", encoding='utf-8') as file:
            file.write(response_vector[0].text)

            data_store.store_to_json(data, "amazon_products_data.json")
            print(f"the scraped data price is {data['Price']}")


def give_urls_to_scrape(excel_filename="amazon_products_data.xlsx", json_filename="amazon_product_review_data.json"):
    """
    Determines which product URLs need to be scraped next based on progress saved in JSON file.
    If a review scraping process was interrupted, this function will return URLs starting from 
    the last URL that was being processed.
    
    Args:
        excel_filename: Path to Excel file containing product URLs
        json_filename: Path to JSON file containing scraped review data
        
    Returns:
        list: List of product URLs that need to be scraped
    """
    
    # Read all product URLs from Excel file
    try:
        df = pd.read_excel(excel_filename)
        if 'Product URL' not in df.columns:
            print(f"Error: 'Product URL' column not found in {excel_filename}")
            return []
        
        product_urls = [str(url).strip() for url in df['Product URL'] if pd.notna(url)]
        print(f"Found {len(product_urls)} product URLs in Excel file")
        
        if not product_urls:
            print("No valid URLs found in Excel file")
            return []
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return []
    
    # If JSON file doesn't exist, return all product URLs
    if not os.path.exists(json_filename) or os.path.getsize(json_filename) == 0:
        print(f"No existing review data found in {json_filename}, will scrape all products")
        return product_urls
    
    # Find the last product URL in the JSON file
    last_url = None
    
    try: 

        # print("JSON SCRAPING CODE BLOCK ...") 

        with open(json_filename, 'r', encoding='utf-8') as f:
            # Read line by line to find the last valid entry
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                try:
                    review_data = json.loads(line)
                    if 'Product URL' in review_data and review_data['Product URL']:
                        last_url = str(review_data['Product URL']).strip() 
                    
                    # print("the last url is ",last_url)

                except json.JSONDecodeError:
                    continue  # Skip invalid JSON lines
    except Exception as e:
        print(f"Error reading JSON file: {str(e)}")
        return product_urls  # If we can't read the file, return all URLs
    
    if not last_url:
        print("No valid product URL found in JSON file, will scrape all products")
        return product_urls
    
    # Find the position of the last scraped URL in our list
    try:
        last_index = product_urls.index(last_url)
        # Return all URLs after the last scraped one (including the last one to ensure we get all reviews)
        remaining_urls = product_urls[last_index+1:] 

        print("the remaining urls are ", remaining_urls)

        print(f"Continuing from product {last_index+1}/{len(product_urls)}: {last_url}")
        return remaining_urls
    except ValueError:
        # If the last URL from JSON isn't in our Excel list, start from the beginning
        print(f"Last scraped URL {last_url} not found in Excel file, will scrape all products")
        return product_urls


def arrange_data_for_ai():
    """
    Converts Excel data into a dictionary format for AI processing.
    Extracts review data from products-reviews-data.xlsx and ASIN from amazon_products_data.xlsx.
    
    Returns:
        list: List of dictionaries, where each dictionary contains data for a single product URL
    """
    
    # Read the reviews data
    try:
        reviews_df = pd.read_excel("products-reviews-data.xlsx")
        print(f"Successfully loaded reviews data with {len(reviews_df)} entries")
    except Exception as e:
        print(f"Error reading reviews data: {str(e)}")
        return []
    
    # Read the products data for ASIN lookup
    try:
        products_df = pd.read_excel("amazon_products_data.xlsx")
        print(f"Successfully loaded products data with {len(products_df)} entries")
    except Exception as e:
        print(f"Error reading products data: {str(e)}")
        # Continue with empty products dataframe
        products_df = pd.DataFrame(columns=['Product URL', 'ASIN'])
    
    # Create a dictionary to map product URLs to ASINs
    asin_lookup = {}
    if 'Product URL' in products_df.columns and 'ASIN' in products_df.columns:
        for _, row in products_df.iterrows():
            if pd.notna(row['Product URL']):
                asin_lookup[str(row['Product URL']).strip()] = str(row['ASIN']).strip() if pd.notna(row['ASIN']) else "No ASIN mentioned"
    
    # Function to extract only date part (month, day, year)
    def extract_date(date_string):
        if not isinstance(date_string, str):
            return ""
        
        # Pattern to match dates like "April 10, 2025" or similar formats
        # Tries to find a month name followed by day and year
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,|\s)\s*\d{4}'
        match = re.search(date_pattern, date_string)
        if match:
            return match.group(0)
        return date_string  # Return original if no date pattern found
    
    # Group the data by product URL
    result = []
    
    # Get unique product URLs
    if 'Product URL' in reviews_df.columns:
        unique_urls = reviews_df['Product URL'].dropna().unique()
        
        for url in unique_urls:
            url_str = str(url).strip()
            product_data = reviews_df[reviews_df['Product URL'] == url]
            
            # Create dictionary for this product
            product_dict = {
                "product_url": url_str,
                "review_types": [],
                "review_date": [],
                "ASIN Number": asin_lookup.get(url_str, "No ASIN mentioned")
            }
            
            # Add review types if column exists
            if 'Review Type' in product_data.columns:
                product_dict["review_types"] = [
                    str(rt).strip() for rt in product_data['Review Type'].dropna().tolist()
                ]
            
            # Add review dates if column exists (extract only date part)
            if 'Review Date' in product_data.columns:
                product_dict["review_date"] = [
                    extract_date(str(rd).strip()) for rd in product_data['Review Date'].dropna().tolist()
                ]
            elif 'Date' in product_data.columns:
                product_dict["review_date"] = [
                    extract_date(str(rd).strip()) for rd in product_data['Date'].dropna().tolist()
                ]
            
            result.append(product_dict)
    
    """
    [{'product_url': 'https://www.amazon.com/TSEB4TEP-Collapsible-S-Shaped-Diameter-Puppies/dp/B0CSJWR41K/ref=sr_1_38', 'review_types': ['5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star'], 'review_date': ['January 7, 2025', 'December 14, 2024', 'March 30, 2025', 'December 28, 2024', 'October 6, 2024', 'February 27, 2025', 'May 5, 2025', 'March 15, 2025', 'May 3, 2025', 'May 10, 2025', 'January 7, 2025', 'December 14, 2024', 'March 30, 2025', 'December 28, 2024', 'October 6, 2024', 'February 27, 2025', 'May 5, 2025', 'March 15, 2025', 'May 3, 2025', 'May 10, 2025', 'January 7, 2025', 'December 14, 2024', 'March 30, 2025', 'December 28, 2024', 'October 6, 2024', 'February 27, 2025', 'May 5, 2025', 'March 15, 2025', 'May 3, 2025', 'May 10, 2025', 'January 7, 2025', 'December 14, 2024', 'March 30, 2025', 'December 28, 2024', 'October 6, 2024', 'February 27, 2025', 'May 5, 2025', 'March 15, 2025', 'May 3, 2025', 'May 10, 2025', 'January 7, 2025', 'December 14, 2024', 'March 30, 2025', 'December 28, 2024', 'October 6, 2024', 'February 27, 2025', 'May 5, 2025', 'March 15, 2025', 'May 3, 2025', 'May 10, 2025'], 'ASIN Number': 'B0CSJWR41K'}, {'product_url': 'https://www.amazon.com/Potaroma-Interactive-Activated-Trjajectory-Chargeable/dp/B0D73TF382/ref=sr_1_51', 'review_types': ['5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star'], 'review_date': ['February 12, 2025', 'April 2, 2025', 'December 31, 2024', 'April 8, 2025', 'April 18, 2025', 'March 1, 2025', 'April 7, 2025', 'April 3, 2025', 'May 4, 2025', 'March 5, 2025', 'February 12, 2025', 'April 2, 2025', 'December 31, 2024', 'April 8, 2025', 'April 18, 2025', 'March 1, 2025', 'April 7, 2025', 'April 3, 2025', 'May 4, 2025', 'March 5, 2025', 'February 12, 2025', 'April 2, 2025', 'December 31, 2024', 'April 8, 2025', 'April 18, 2025', 'March 1, 2025', 'April 7, 2025', 'April 3, 2025', 'May 4, 2025', 'March 5, 2025', 'February 12, 2025', 'April 2, 2025', 'December 31, 2024', 'April 8, 2025', 'April 18, 2025', 'March 1, 2025', 'April 7, 2025', 'April 3, 2025', 'May 4, 2025', 'March 5, 2025', 'February 12, 2025', 'April 2, 2025', 'December 31, 2024', 'April 8, 2025', 'April 18, 2025', 'March 1, 2025', 'April 7, 2025', 'April 3, 2025', 'May 4, 2025', 'March 5, 2025'], 'ASIN Number': 'B0D73TF382'}, {'product_url': 'https://www.amazon.com/31Pcs-Launcher-Interactive-Indoor-Kitten/dp/B0CN3N4DNH/ref=sr_1_10', 'review_types': ['5.0 star', '5.0 star', '4.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '4.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '4.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '4.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '4.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '4.0 star'], 'review_date': ['May 9, 2025', 'May 8, 2025', 'March 5, 2025', 'April 20, 2025', 'May 13, 2025', 'April 18, 2025', 'April 7, 2025', 'May 7, 2025', 'April 18, 2025', 'May 11, 2025', 'May 9, 2025', 'May 8, 2025', 'March 5, 2025', 'April 20, 2025', 'May 13, 2025', 'April 18, 2025', 'April 7, 2025', 'May 7, 2025', 'April 18, 2025', 'May 11, 2025', 'May 9, 2025', 'May 8, 2025', 'March 5, 2025', 'April 20, 2025', 'May 13, 2025', 'April 18, 2025', 'April 7, 2025', 'May 7, 2025', 'April 18, 2025', 'May 11, 2025', 'May 9, 2025', 'May 8, 2025', 'March 5, 2025', 'April 20, 2025', 'May 13, 2025', 'April 18, 2025', 'April 7, 2025', 'May 7, 2025', 'April 18, 2025', 'May 11, 2025', 'May 9, 2025', 'May 8, 2025', 'March 5, 2025', 'April 20, 2025', 'May 13, 2025', 'April 18, 2025', 'April 7, 2025', 'May 7, 2025', 'April 18, 2025', 'May 11, 2025'], 'ASIN Number': 'B0CN3N4DNH'}, {'product_url': 'https://www.amazon.com/UPSKY-Colorful-Interactive-Physical-Exercise/dp/B07FZVML3X/ref=sr_1_46', 'review_types': ['5.0 star', '5.0 star', '5.0 star', '4.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '3.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star'], 'review_date': ['April 19, 2025', 'April 28, 2025', 'March 24, 2025', 'April 10, 2025', 'February 8, 2025', 'May 14, 2025', 'January 26, 2025', 'April 14, 2025', 'April 19, 2025', 'April 21, 2025', 'April 19, 2025', 'April 28, 2025', 'March 24, 2025', 'April 10, 2025', 'February 8, 2025', 'May 14, 2025', 'January 26, 2025', 'April 14, 2025', 'April 19, 2025', 'April 21, 2025', 'April 19, 2025', 'April 28, 2025', 'March 24, 2025', 'April 10, 2025', 'February 8, 2025', 'May 14, 2025', 'January 26, 2025', 'April 14, 2025', 'April 19, 2025', 'April 21, 2025', 'April 19, 2025', 'April 28, 2025', 'March 24, 2025', 'April 10, 2025', 'February 8, 2025', 'May 14, 2025', 'January 26, 2025', 'April 14, 2025', 'April 19, 2025', 'April 21, 2025', 'April 19, 2025', 'April 28, 2025', 'March 24, 2025', 'April 10, 2025', 'February 8, 2025', 'May 14, 2025', 'January 26, 2025', 'April 14, 2025', 'April 19, 2025', 'April 21, 2025'], 'ASIN Number': 'B07FZVML3X'}, {'product_url': 'https://www.amazon.com/Yeowww-Catnip-Variety-Banana-Rainbow/dp/B00JKSE4Q4/ref=sr_1_54', 'review_types': ['5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '5.0 star', '4.0 star', '5.0 star', '5.0 star', '5.0 star'], 'review_date': ['March 18, 2025', 'November 17, 2024', 'March 20, 2025', 'March 11, 2025', 'March 25, 2025', 'May 3, 2025', 'April 18, 2024', 'January 12, 2025', 'May 14, 2025', 'May 11, 2025', 'March 18, 2025', 'November 17, 2024', 'March 20, 2025', 'March 11, 2025', 'March 25, 2025', 'May 3, 2025', 'April 18, 2024', 'January 12, 2025', 'May 14, 2025', 'May 11, 2025', 'March 18, 2025', 'November 17, 2024', 'March 20, 2025', 'March 11, 2025', 'March 25, 2025', 'May 3, 2025', 'April 18, 2024', 'January 12, 2025', 'May 14, 2025', 'May 11, 2025', 'March 18, 2025', 'November 17, 2024', 'March 20, 2025', 'March 11, 2025', 'March 25, 2025', 'May 3, 2025', 'April 18, 2024', 'January 12, 2025', 'May 14, 2025', 'May 11, 2025', 'March 18, 2025', 'November 17, 2024', 'March 20, 2025', 'March 11, 2025', 'March 25, 2025', 'May 3, 2025', 'April 18, 2024', 'January 12, 2025', 'May 14, 2025', 'May 11, 2025'], 'ASIN Number': 'B00JKSE4Q4'}]
    """

    print(f"Organized data for {len(result)} unique products")
    return result 

# ================================================================================
# Scrap product reviews from Amazon product page 
# functions are following ... 
# ================================================================================

def scrap_product_reviews(html_content, product_url):
    """
    This function is used to scrap the reviews from the amazon product page ... 
    """

    soup = BeautifulSoup(html_content, 'html.parser')
    reviews = []

    # Extract ratings with percentage from histogram
    ratings_with_percentage = ""
    histogram_section = soup.find('div', class_='a-section histogram')
    
    if histogram_section:
        rating_links = histogram_section.find_all('a', class_='a-link-normal histogram-row-container')
        percentage_list = []
        
        for link in rating_links:
            if link.has_attr('aria-label'):
                percentage_list.append(link['aria-label'])
        
        if percentage_list:
            ratings_with_percentage = " , ".join(percentage_list)

    # All reviews are in <li> tags with data-hook="review"
    review_blocks = soup.find_all('li', {'data-hook': 'review'})

    for block in review_blocks:
        review_data = {}

        # (1) Customer Name
        name_tag = block.select_one('div.a-profile-content > span.a-profile-name')
        review_data["Customer Name"] = name_tag.get_text(strip=True) if name_tag else "N/A"

        # (2) Review Type (Star Rating)
        star_tag = block.find('i', {'data-hook': 'review-star-rating'})
        if not star_tag:
            star_tag = block.find('i', {'data-hook': 'cmps-review-star-rating'})
        if star_tag:
            star_text = star_tag.find('span').get_text(strip=True)
            review_data["Review Type"] = star_text.split()[0] + " star" if star_text else "N/A"
        else:
            review_data["Review Type"] = "N/A"

        # (3) Review Headline
        headline_tag = block.find('a', {'data-hook': 'review-title'})
        if headline_tag:
            span = headline_tag.find('span')
            review_data["Review Headline"] = span.get_text(strip=True) if span else "N/A"
        else:
            review_data["Review Headline"] = "N/A"

        # (4) Review Text
        review_body = block.find('span', {'data-hook': 'review-body'})
        if review_body:
            inner_span = review_body.find('span')
            review_data["Review Text"] = inner_span.get_text(strip=True) if inner_span else "N/A"
        else:
            review_data["Review Text"] = "N/A"

        # (5) Date
        date_tag = block.find('span', {'data-hook': 'review-date'})
        review_data["Date"] = date_tag.get_text(strip=True) if date_tag else "N/A"
        review_data['Product URL'] = product_url
        
        # Add ratings percentage information to each review
        review_data['Ratings with percentage'] = ratings_with_percentage

        reviews.append(review_data)

    return reviews


def generate_review_urls(product_url, pages=5):
    # Extract ASIN from the product URL using regex
    match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
    if not match:
        raise ValueError("ASIN not found in URL")

    asin = match.group(1)
    base_url = f"https://www.amazon.com/product-reviews/{asin}/ref=cm_cr_arp_d_paging_btm_next_2?ie=UTF8&reviewerType=all_reviews&pageNumber="

    # Generate URLs for each page number
    urls = [base_url + str(page) for page in range(1, pages + 1)]
    return urls


def give_urls_to_scrape(excel_filename="amazon_products_data.xlsx", json_filename="amazon_product_review_data.json"):
    """
    Determines which product URLs need to be scraped next based on progress saved in JSON file.
    If a review scraping process was interrupted, this function will return URLs starting from 
    the last URL that was being processed.
    
    Args:
        excel_filename: Path to Excel file containing product URLs
        json_filename: Path to JSON file containing scraped review data
        
    Returns:
        list: List of product URLs that need to be scraped
    """
    
    # Read all product URLs from Excel file
    try:
        df = pd.read_excel(excel_filename)
        if 'Product URL' not in df.columns:
            print(f"Error: 'Product URL' column not found in {excel_filename}")
            return []
        
        product_urls = [str(url).strip() for url in df['Product URL'] if pd.notna(url)]
        print(f"Found {len(product_urls)} product URLs in Excel file")
        
        if not product_urls:
            print("No valid URLs found in Excel file")
            return []
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return []
    
    # If JSON file doesn't exist, return all product URLs
    if not os.path.exists(json_filename) or os.path.getsize(json_filename) == 0:
        print(f"No existing review data found in {json_filename}, will scrape all products")
        return product_urls
    
    # Find the last product URL in the JSON file
    last_url = None
    
    try: 

        # print("JSON SCRAPING CODE BLOCK ...") 

        with open(json_filename, 'r', encoding='utf-8') as f:
            # Read line by line to find the last valid entry
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                try:
                    review_data = json.loads(line)
                    if 'Product URL' in review_data and review_data['Product URL']:
                        last_url = str(review_data['Product URL']).strip() 
                    
                    # print("the last url is ",last_url)

                except json.JSONDecodeError:
                    continue  # Skip invalid JSON lines
    except Exception as e:
        print(f"Error reading JSON file: {str(e)}")
        return product_urls  # If we can't read the file, return all URLs
    
    if not last_url:
        print("No valid product URL found in JSON file, will scrape all products")
        return product_urls
    
    # Find the position of the last scraped URL in our list
    try:
        last_index = product_urls.index(last_url)
        # Return all URLs after the last scraped one (including the last one to ensure we get all reviews)
        remaining_urls = product_urls[last_index+1:] 

        print("the remaining urls are ", remaining_urls)

        print(f"Continuing from product {last_index+1}/{len(product_urls)}: {last_url}")
        return remaining_urls
    except ValueError:
        # If the last URL from JSON isn't in our Excel list, start from the beginning
        print(f"Last scraped URL {last_url} not found in Excel file, will scrape all products")
        return product_urls

def generate_product_review_urls(): 

    reviews_urls_list = []

    product_urls = give_urls_to_scrape()

    for product_url in product_urls:
        review_urls = generate_review_urls(product_url)
        reviews_urls_list.extend(review_urls)

    return reviews_urls_list

def split_list(lst, n):
    """Split list lst into n nearly equal sublists"""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

async def process_tab(page, url_list, tab_idx):
    for review_url in url_list:
        try:
            await page.goto(review_url)
            await asyncio.sleep(2)
            html_content = await page.content()
            data_list = scrap_product_reviews(html_content, review_url)
            if data_list:
                for review_data in data_list:
                    data_store.store_to_json(review_data, "amazon_product_review_data.json")
                    print(f"[Tab {tab_idx+1}] Scraped data is ", review_data)
            else:
                print(f"[Tab {tab_idx+1}] No reviews found on this page")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[Tab {tab_idx+1}] Error processing {review_url}: {e}")

async def process_tabs_for_bulk_scraping(page, url_list, tab_idx):

    for _url in url_list:
        try:
            await page.goto(_url)
            await asyncio.sleep(1)
            html_content = await page.content()
            products_data = scrap_product_data(html_content, _url)
            if products_data:
                    data_store.store_to_json(products_data, "amazon_products_data.json")
                    print(f"[Tab {tab_idx+1}] Scraped data is ", products_data)
            else:
                print(f"[Tab {tab_idx+1}] No data found on this page")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[Tab {tab_idx+1}] Error processing {_url}: {e}")


# async def check_captcha_presence(page) -> bool:
#     """
#     Returns True if the normal page content is present (no captcha),
#     False if captcha is present or on error.
#     """
#     try:
#         html = await page.content(timeout=10000)  # 10 seconds timeout
#         return '<input id="nav-search-submit-button"' in html
#     except TimeoutError:
#         print("Timeout while checking for captcha presence.")
#         return False
#     except Exception as e:
#         print(f"Exception while checking for captcha presence: {e}")
        # return False

async def login_and_perform_bulk_scraping(email, password):

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        login_url = "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
        await page.goto(login_url)
        await asyncio.sleep(3)
        try:
            await page.wait_for_selector('text="Continue shopping"', timeout=2000)
            await page.click('text="Continue shopping"')
            await asyncio.sleep(1)
        except Exception:
            pass 

        pyautogui.write(email)
        pyautogui.press('enter') 
        time.sleep(3)

        pyautogui.write(password)
        pyautogui.press('enter') 
        time.sleep(30) #time-sleep to handle captcha if it appears manually

        list_ = read_urls_from_file('amazon-product-links.txt')

        print(f"Total product URLs to scrape: {len(list_)}")

        sublists = split_list(list_, 7)
        pages = [await context.new_page() for _ in range(7)]
        tasks = []
        for idx, (tab_page, url_list) in enumerate(zip(pages, sublists)):
            tasks.append(process_tabs_for_bulk_scraping(tab_page, url_list, idx))
        await asyncio.gather(*tasks)
        await browser.close()

        data_store.save_data_to_excel("amazon_products_data.json", "amazon_products_data.xlsx")

async def login_and_scrape_reviews_async(email, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        login_url = "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0"
        await page.goto(login_url)
        await asyncio.sleep(3)
        try:
            await page.wait_for_selector('text="Continue shopping"', timeout=2000)
            await page.click('text="Continue shopping"')
            await asyncio.sleep(1)
        except Exception:
            pass 

        pyautogui.write(email)
        pyautogui.press('enter') 
        time.sleep(3)

        pyautogui.write(password)
        pyautogui.press('enter') 
        time.sleep(30)

        # if await check_captcha_presence(page):
        #     print("No captcha detected.") 
        # else:
        #     time.sleep(30)
        #     print("Captcha detected!")

        # Now login is done, open 7 tabs and process in parallel 

        all_review_urls = generate_product_review_urls() 
        print(f"Total review URLs to scrape: {len(all_review_urls)}") 
        time.sleep(4)

        sublists = split_list(all_review_urls, 7)
        pages = [await context.new_page() for _ in range(7)]

        tasks = []
        for idx, (tab_page, url_list) in enumerate(zip(pages, sublists)):
            tasks.append(process_tab(tab_page, url_list, idx))
        await asyncio.gather(*tasks)

        await browser.close()
        data_store.save_data_to_excel("amazon_product_review_data.json", "amazon_product_review_data.xlsx")
        # print("All data saved to Excel.")

if __name__ == "__main__":

    print("start...")
    load_dotenv()
    email = os.getenv("AMAZON_ACCOUNT_EMAIL")
    password = os.getenv("AMAZON_ACCOUNT_PASSWORD")

    # asyncio.run(login_and_scrape_reviews_async(email, password)) 
    asyncio.run(login_and_perform_bulk_scraping(email, password))

    # data_store.save_data_to_excel("amazon_product_review_data.xlsx", "amazon_product_review_data.json")

    # with open("amazon_source_code.txt", "r", encoding="utf-8") as file:
        # html = file.read()

    # product_url = "https://www.amazon.com/Hanes-Comfort-Seamless-Boyshort-Assorted/dp/B085B4MV8F/ref=sr_1_47"
    # review_scraping_process()  

    # data_store.save_data_to_excel('products-reviews-data.xlsx', 'amazon_product_review_data.json')

    # results = arrange_data_for_ai()
    # print(results)
    
#     data_vector = scrap_product_data(html,product_url)
#     print(data_vector)

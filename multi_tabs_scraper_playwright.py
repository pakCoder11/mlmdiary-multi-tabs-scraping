from cmath import log
from bs4 import BeautifulSoup
import data_store 
import bot_functions 
import time 
import re
import pandas as pd
import json 
import os
import pyautogui 
from dotenv import load_dotenv
from playwright.async_api import async_playwright   
import asyncio

def scrape_data_from_url(html_content,url):
    """
    Extracts profile data from the given HTML content.
    Returns a dictionary with keys: 'name', 'location', 'company', 'plan', 'phone'.
    If a value is not found, it is set to None.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    data = {
        'name': None,
        'location': None,
        'company': None,
        'plan': None,
        'phone': None,
        'profile_url': url
    }

    profile_cont = soup.find("div", class_="profile_cont")
    if not profile_cont:
        return data

    # Name
    h5 = profile_cont.find("h5")
    if h5:
        data['name'] = h5.get_text(strip=True) or None

    # Profile list items
    profile_list = profile_cont.find("ul", class_="profile_list")
    if profile_list:
        for li in profile_list.find_all("li"):
            # Location
            img = li.find("img")
            span = li.find("span")
            if img and "location" in img.get("data-src", "") and span:
                data['location'] = span.get_text(strip=True) or None
            # Company
            if "company" in li.get("class", []):
                data['company'] = li.get_text(strip=True) or None
            # Plan
            if img and "planning" in img.get("data-src", "") and span:
                data['plan'] = span.get_text(strip=True) or None
            # Phone
            a = li.find("a", href=True)
            if a and a["href"].startswith("tel:"):
                phone_span = a.find("span")
                if phone_span:
                    data['phone'] = phone_span.get_text(strip=True) or None

    return data

def split_list(lst, n):
    """Split list lst into n nearly equal sublists"""
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

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


def extract_links_from_database(html):
    """
    Extracts all profile links from divs with class 'database' in the given HTML.
    Returns a list of profile URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    profile_links = []
    for db_div in soup.find_all("div", class_="database"):
        a_tag = db_div.find("a", class_="profile_btn")
        if a_tag and a_tag.get("href"):
            profile_links.append(a_tag["href"])  

            with open("profile_links.txt", "a") as f:
                f.write(f"{a_tag['href']}\n")

    return profile_links

async def process_tabs_for_bulk_scraping(page, url_list, tab_idx, scraping_flag):

    """
    This is a function to process multiple tabs for bulk scraping.
    It takes a Playwright page object, a list of URLs, an index for the tab

    """

    for _url in url_list:
        try:
            await page.goto(_url)
            await asyncio.sleep(1)
            html_content = await page.content()

            if scraping_flag == 0:
                pass
            elif scraping_flag == 1:

                profile_data = scrape_data_from_url(html_content,_url) # --> this is where your scraping function is called and extract data from the page ... return a data into the dictionary ...

                # if the dictionary found then store the data intot the file ...  
                # and also delete the url from the file ... 
                # this is done to avoid duplicate scraping of the same url ...

                if profile_data:
                        data_store.store_to_json(profile_data, "mlmdiary-profiles-data.json") 
                        print(f"[Tab {tab_idx+1}] Scraped data is ", profile_data) 
                        delete_url_from_file(_url, "profile_links.txt")
                else:
                    print(f"[Tab {tab_idx+1}] No data found on this page")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[Tab {tab_idx+1}] Error processing {_url}: {e}")

# async def login(page, email="9907652783", password="123Ram990"):
async def login(page):
    
    """
    Login to the website using Playwright by interacting with form elements
    """

    load_dotenv()
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    try:
        # Wait for form elements to be present
        await page.wait_for_selector('#phone')
        await page.wait_for_selector('#password')
        await page.wait_for_selector('#btnlogin')

        # Fill in the form
        await page.fill('#phone', email)
        await page.fill('#password', password)
        
        # Click the login button
        await page.click('#btnlogin')
        
        # Wait for navigation/login to complete
        await page.wait_for_load_state('networkidle')
        
        print("Login successful")
        
    except Exception as e:
        print(f"Login failed: {str(e)}")

def delete_url_from_file(url_to_delete, file_path):
    """
    Delete a specific URL from the file.
    
    Args:
        url_to_delete (str): The URL to be deleted
        file_path (str): Path to the file containing URLs (default: links.txt)
    """
    try:
        # Read all URLs from file
        with open(file_path, 'r') as file:
            urls = file.readlines()
        
        # Clean URLs (remove whitespace/newlines)
        urls = [url.strip() for url in urls]
        
        # Check if URL exists in file
        if url_to_delete not in urls:
            print(f"URL {url_to_delete} not found in {file_path}")
            return
        
        # Remove the URL and rewrite the file
        urls.remove(url_to_delete)
        
        # # Write remaining URLs back to file
        with open(file_path, 'w') as file:
            for url in urls:
                file.write(f"{url}\n")
        print(f"Successfully removed {url_to_delete} from {file_path}")
            
    except FileNotFoundError:
        print(f"File {file_path} not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

async def login_and_perform_bulk_scraping(email, password):

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to login page
        await page.goto("https://www.mlmdiary.com/login")
        
        # Perform login
        await login(page)
        
        # Wait for any post-login processing
        await asyncio.sleep(2)

        # scraping_flag = 1 read urls from profile_links.txt
        # scraping_flag = 0 read urls links.txt
        
        list_ = read_urls_from_file('profile_links.txt')

        print(f"Total product URLs to scrape: {len(list_)}")

        sublists = split_list(list_, 7)
        pages = [await context.new_page() for _ in range(7)]
        tasks = []
        for idx, (tab_page, url_list) in enumerate(zip(pages, sublists)):
            tasks.append(process_tabs_for_bulk_scraping(tab_page, url_list, idx, scraping_flag=1))
        await asyncio.gather(*tasks)
        await browser.close()

        data_store.save_data_to_excel("mlmdiary-profiles-data.json", "mlmdiary-profiles-data.xlsx")

asyncio.run(login_and_perform_bulk_scraping())
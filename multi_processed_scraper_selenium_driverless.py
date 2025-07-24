import asyncio
from concurrent.futures import ProcessPoolExecutor
import pyautogui
from selenium_driverless import webdriver
from bs4 import BeautifulSoup
import json
import re
import time
import multiprocessing
import bot_functions
import data_store
import math

def write_links(file_path, urls):
    with open(file_path, 'a+') as file:
        for url in urls:
            file.write(f"{url}\n")

def auto_login(email="9907652783", password="123Ram990"):
    """
    This function is used to auto login ...
    """
    bot_functions.ClickImageOnScreen("login.png", 1)
    time.sleep(2)
    pyautogui.press("tab")
    time.sleep(1)
    pyautogui.press("tab")
    pyautogui.write(email)
    time.sleep(1)
    pyautogui.press("tab")
    pyautogui.write(password)
    pyautogui.press("enter")

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

def scrape_data_from_url(html_content, url):
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

async def scrape_urls_in_context(context, urls, context_id):
    """
    Scrapes data from a list of URLs in a specific browser context.
    """
    results = []
    for url in urls:
        try:
            await context.get(url, wait_load=False)
            await asyncio.sleep(2)
            page_source = await context.page_source
            profile_data = scrape_data_from_url(page_source, url)
            print(f"Context {context_id}: Extracted data from {url}")
            data_store.store_to_json(profile_data, "mlmdiary-profiles-data.json")
            print(f"Context {context_id}: Scraped Data: {profile_data}")
            results.append(profile_data)
        except Exception as e:
            print(f"Context {context_id}: Error processing {url}: {e}")
    return results

async def scrape_profiles(all_urls):
    """
    Splits URLs into 7 parts and processes them concurrently in 7 browser contexts.
    """
    async with webdriver.Chrome() as browser:
        # Perform login in the default context
        await browser.get("https://www.mlmdiary.com/login")
        time.sleep(5)
        auto_login()
        time.sleep(10)

        # Split URLs into 7 parts
        num_contexts = 7
        urls_per_context = math.ceil(len(all_urls) / num_contexts)
        url_chunks = [all_urls[i:i + urls_per_context] for i in range(0, len(all_urls), urls_per_context)]

        # Create browser contexts (including the default one)
        contexts = [browser.current_context]  # Default context
        for i in range(num_contexts - 1):
            new_context = await browser.new_context()
            # Navigate to login page in each new context to ensure session
            await new_context.get("https://www.mlmdiary.com/login")
            time.sleep(5)
            auto_login()
            time.sleep(30)
            contexts.append(new_context)

        # Create tasks for each context to scrape its chunk of URLs
        tasks = []
        for i, (context, chunk) in enumerate(zip(contexts, url_chunks)):
            if chunk:  # Only create tasks for non-empty chunks
                tasks.append(scrape_urls_in_context(context, chunk, i + 1))

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

    # Save data to Excel after all scraping is done
    data_store.save_data_to_excel("mlmdiary-profiles-data.json", "mlmdiary-profiles-data.xlsx")

# Read URLs from file
with open("profile_links.txt", "r") as f:
    urls = [line.strip() for line in f.readlines() if line.strip()]

# Run the scraper
asyncio.run(scrape_profiles(urls))
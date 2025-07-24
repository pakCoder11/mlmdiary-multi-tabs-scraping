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

def write_links(file_path, urls):
    with open(file_path, 'a+') as file:
        for url in urls:
            file.write(f"{url}\n")

def auto_login(email="9907652783",password="123Ram990"):
    """
    This function is used to auto login ... 
    """ 

    bot_functions.ClickImageOnScreen("login.png",1)
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
    
async def extract_links_from_pages(all_urls):
    async with webdriver.Chrome() as driver:
        results = []
        processed_urls = []

        await driver.get("https://www.mlmdiary.com/login")
        time.sleep(5) 
        auto_login()
        time.sleep(10)

        for url in all_urls:
            
            await driver.get(url,wait_load=False) 
            await asyncio.sleep(2) 
            page_source = await driver.page_source 

            # with open("page_source.html", "w", encoding='utf-8') as f:
            #     f.write(page_source)
            
            links = extract_links_from_database(page_source)
            print(f"Extracted {len(links)} links from {url}")

            write_links("profile_links.txt", links)

            # break
            # code to for to call a scraping function ... extract_data is a scraping function ...
            # data = await extract_data(page_source, driver) 
            # results.append(data)
            # processed_urls.append(url)

        # with open("data.json", "a", encoding='utf-8') as f:
            # for data in results:
                # json.dump(data, f, ensure_ascii=False)
                # f.write(",\n")

        # Remove processed URLs from the main URL list
        # remaining_urls = [url for url in all_urls if url not in processed_urls]
        # write_links("links.txt", remaining_urls)

async def scrape_profiles(all_urls):
    async with webdriver.Chrome() as driver:
        results = []
        processed_urls = []

        await driver.get("https://www.mlmdiary.com/login")
        time.sleep(5) 
        auto_login()
        time.sleep(10)

        for url in all_urls:

            try:
                await driver.get(url,wait_load=False) 
                await asyncio.sleep(2) 
                page_source = await driver.page_source 

                # with open("page_source.html", "w", encoding='utf-8') as f:
                #     f.write(page_source)

                profile_data = scrape_data_from_url(page_source,url)
                print(f"Extracted data from {url}") 

                data_store.store_to_json(profile_data, "mlmdiary-profiles-data.json")
                print(f"Scraped Data: {profile_data}")
            
            except Exception as e:
                print(f"Error processing {url}: {e}")

            # break
            # code to for to call a scraping function ... extract_data is a scraping function ...
            # data = await extract_data(page_source, driver) 
            # results.append(data)
            # processed_urls.append(url)

        # with open("data.json", "a", encoding='utf-8') as f:
            # for data in results:
                # json.dump(data, f, ensure_ascii=False)
                # f.write(",\n")

        # Remove processed URLs from the main URL list
        # remaining_urls = [url for url in all_urls if url not in processed_urls]
        # write_links("links.txt", remaining_urls)
    
    data_store.save_data_to_excel("mlmdiary-profiles-data.json", "mlmdiary-profiles-data.xlsx")

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

with open("profile_links.txt", "r") as f:
    urls = [line.strip() for line in f.readlines() if line.strip()]
    
# asyncio.run(extract_links_from_pages(urls))  # Example usage
asyncio.run(scrape_profiles(urls))  # Example usage

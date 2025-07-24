# Web Scraping Project for MLM Business

## Overview
This project is a web scraping tool designed to extract data from multiple tabs of the website [mlmldiary.com](https://www.mlmldiary.com), an Indian platform for Multi-Level Marketing (MLM) businesses. The script uses Playwright in Python to automate browser actions, including logging into the website, navigating through multiple tabs, and extracting data from each tab.

This tool was developed for an Indian client running an MLM business in India. The script is well-documented with comments in the `multi_tabs_scraper_playwright.py` file and can be modified to suit specific needs.

## Prerequisites
To run the script, you need to install the following Python packages:
- `playwright`
- `pandas`
- `openpyxl`
- `asyncio`

Install the latest versions of these packages using the following command:
```bash
pip install playwright pandas openpyxl
```
Additionally, install the Playwright browsers by running:
```bash
playwright install
```

## Usage
1. Ensure all prerequisites are installed.
2. Modify the `multi_tabs_scraper_playwright.py` script as needed for your specific use case (e.g., updating login credentials or target data fields).
3. Run the script using the following command:
```bash
python multi_tabs_scraper_playwright.py
```

The script will:
- Log in to [mlmldiary.com](https://www.mlmldiary.com).
- Navigate through the specified tabs.
- Extract and save the data (e.g., to an Excel file using `pandas` and `openpyxl`).

## Project Structure
- `multi_tabs_scraper_playwright.py`: The main Python script containing the web scraping logic with detailed comments for customization.

## Customization
You can modify the script to:
- Target different tabs or sections of the website.
- Adjust the data extraction logic to capture specific fields.
- Change the output format (e.g., CSV, JSON) by updating the `pandas` export functions.

Refer to the inline comments in `multi_tabs_scraper_playwright.py` for guidance on customization.

## Links
- **YouTube Channel**: [Saad Khan](https://www.youtube.com/@saadkhan883)
- **WhatsApp Group**: [Join here](https://chat.whatsapp.com/FIGWnTfgUHGLtVOYJ8I5OI)
- **Fiverr**: [Hire me for bot development](https://www.fiverr.com/bot_dev_96/develop-bots-to-automate-your-social-media-postings)

## Notes
- Ensure you have permission to scrape data from [mlmldiary.com](https://www.mlmldiary.com) and comply with their terms of service.
- The script is designed for educational and legitimate business purposes. Use responsibly.

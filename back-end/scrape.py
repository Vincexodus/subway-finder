#!/usr/bin/env python3
"""
Subway Outlet Scraper
Scrapes Subway outlet data from subway.com.my with Kuala Lumpur filter
"""

from multiprocessing.connection import Client
import sqlite3
import time
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dataclasses import dataclass
from typing import List, Optional
import logging
from bs4.element import Tag
from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SubwayOutlet:
    name: str
    address: str
    operating_hours: str
    waze_link: Optional[str] = None

class SubwayScraper:
    def __init__(self, headless=True):
        self.base_url = "https://subway.com.my/find-a-subway"
        self.outlets = []
        self.setup_driver(headless)
        self.setup_supabase()
    
    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def setup_supabase(self):
            """Initialize Supabase client"""
            if not SUPABASE_URL or not SUPABASE_KEY:
                raise ValueError("Supabase URL and Key must be set in environment variables.")
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")

    def save_to_database(self, outlets):
        """Save scraped outlets to Supabase"""
        saved_count = 0
        for outlet in outlets:
            try:
                data = {
                    "name": outlet.name or "",
                    "address": outlet.address or "",
                    "operating_hours": outlet.operating_hours or "",
                    "waze_link": outlet.waze_link or "",
                }

                response = self.supabase.table("outlets").upsert(data, on_conflict="name,address").execute()
                if response.data:
                    saved_count += 1
                else:
                    logger.error(f"Supabase error: {response.data}")
            except Exception as e:
                logger.error(f"Error saving outlet {outlet.name}: {e}")
                continue
        logger.info(f"Saved {saved_count} outlets to Supabase")
        return saved_count
    
    def filter_by_kuala_lumpur(self):
        """Filter search results by Kuala Lumpur"""
        try:
            logger.info("Navigating to Subway store locator...")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            try:
                search_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[id*='fp_searchAddress']"))
                )
            except TimeoutException:
                logger.warning("Search input not found by ID")
                search_input = None
            
            if search_input:
                logger.info("Found search input, entering 'Kuala Lumpur'")
                search_input.clear()
                search_input.send_keys("Kuala Lumpur")
                time.sleep(2)
                
                try:
                    search_btn = self.driver.find_element(By.CSS_SELECTOR, "button[id*='fp_searchAddressBtn']")
                    search_btn.click()
                    time.sleep(3)
                    logger.info("Clicked search button")
                except NoSuchElementException:
                    logger.warning(f"Search button not found with selector")
            
        except Exception as e:
            logger.error(f"Error filtering by Kuala Lumpur: {e}")
            return False
        return True
    
    def scrape_outlet_data(self):
        """Scrape outlet data from current page"""
        outlets_on_page = []
        
        try:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='fp_listitem']")
                if elements:
                    outlet_elements = elements
                    logger.info(f"Found {len(elements)} outlets using selector: [class*='fp_listitem']")
                    
            except:
                logger.warning("Failed to find outlets using primary selector, trying alternative methods")
                outlet_elements = []
            
            if not outlet_elements:
                # Fallback: scrape from page source
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for patterns in the HTML
                potential_containers = soup.find_all(['div', 'li', 'article'], 
                    class_=re.compile(r'store|outlet|location|shop', re.I))
                
                if potential_containers:
                    logger.info(f"Found {len(potential_containers)} potential outlet containers")
                    outlet_elements = potential_containers
            
            for element in outlet_elements:
                try:
                    outlet_data = self.extract_outlet_info(element)
                    if outlet_data and outlet_data.name and outlet_data.address:
                        outlets_on_page.append(outlet_data)
                        logger.info(f"Extracted outlet: {outlet_data.name}")
                except Exception as e:
                    logger.warning(f"Error extracting outlet data: {e}")
                    continue
            
            return outlets_on_page
            
        except Exception as e:
            logger.error(f"Error scraping outlet data: {e}")
            return []
    
    def extract_outlet_info(self, element):
        """Extract outlet information from HTML element (BeautifulSoup Tag or Selenium WebElement)"""
        try:
            # Convert Selenium element to BeautifulSoup if needed
            if not hasattr(element, 'find'):
                html = element.get_attribute('outerHTML')
                soup_element = BeautifulSoup(html, 'html.parser')
            else:
                soup_element = element

            # Name
            name_elem = soup_element.select_one('h4')
            name = name_elem.get_text(strip=True) if name_elem else ""

            # Address (first <p> in .infoboxcontent)
            address_elem = soup_element.select_one('.infoboxcontent p')
            address = address_elem.get_text(strip=True) if address_elem else ""

            # Operating hours (all <p> in .infoboxcontent except first and last)
            p_tags = soup_element.select('.infoboxcontent p')
            hours = []
            for p in p_tags[1:-1]:
                text = p.get_text(strip=True)
                if text:
                    hours.append(text)
            operating_hours = " | ".join(hours) if hours else "Not specified"

            # Waze link
            waze_link = None
            for a in soup_element.select('.directionButton a'):
                href = a.get('href', '')
                if href and isinstance(href, str) and 'waze.com' in href:
                    waze_link = href
                    break


            if name and address:
                # print(f"Extracted outlet: {name}, Address: {address}, Hours: {operating_hours}, Waze: {waze_link}")
                return SubwayOutlet(
                    name=name,
                    address=address,
                    operating_hours=operating_hours,
                    waze_link=waze_link,
                )
            return None
        except Exception as e:
            logger.error(f"Error extracting outlet info: {e}")
            return None
    
    def handle_pagination(self):
        """Handle pagination to scrape all pages"""
        all_outlets = []
        page_num = 1
        
        while True:
            logger.info(f"Scraping page {page_num}")
            
            # Scrape current page
            outlets_on_page = self.scrape_outlet_data()
            
            if not outlets_on_page:
                logger.warning(f"No outlets found on page {page_num}")
                break
            
            all_outlets.extend(outlets_on_page)
            logger.info(f"Found {len(outlets_on_page)} outlets on page {page_num}")
            
            # Look for next page button
            next_button_found = False
            next_selectors = [
                "a[aria-label*='next']",
                ".next",
                ".pagination-next",
                "a:contains('Next')",
                ".page-next",
                "[class*='next']"
            ]
            
            for selector in next_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button.is_enabled() and next_button.is_displayed():
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(3)
                        next_button_found = True
                        logger.info(f"Clicked next button, moving to page {page_num + 1}")
                        break
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.warning(f"Error clicking next button: {e}")
                    continue
            
            if not next_button_found:
                logger.info("No more pages found")
                break
            
            page_num += 1
            
            # Safety limit
            if page_num > 20:
                logger.warning("Reached maximum page limit (20)")
                break
        
        return all_outlets
    
    def run_scraping(self):
        """Main scraping workflow"""
        try:
            logger.info("Starting Subway outlet scraping...")
            
            # Filter by Kuala Lumpur
            if not self.filter_by_kuala_lumpur():
                logger.error("Failed to filter by Kuala Lumpur")
                return
            
            # Handle pagination and scrape all pages
            all_outlets = self.handle_pagination()
            
            if all_outlets:
                # Save to database
                saved_count = self.save_to_database(all_outlets)
                logger.info(f"Scraping completed. Total outlets scraped: {len(all_outlets)}, Saved: {saved_count}")
            else:
                logger.warning("No outlets were scraped")
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if hasattr(self, 'driver'):
            self.driver.quit()
        logger.info("Cleanup completed")

def main():
    """Main function to run the scraper"""
    scraper = SubwayScraper(headless=False)  # Set to True for headless mode
    scraper.run_scraping()

if __name__ == "__main__":
    main()#!/usr/bin/env python3
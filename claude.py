import time
import json
import logging
import smtplib
import schedule
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flight_scraper.log'),
        logging.StreamHandler()
    ]
)

class FlightPriceScraper:
    def __init__(self):
        # Email configuration
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('SENDER_EMAIL')
        self.sender_password = os.getenv('SENDER_PASSWORD')
        self.receiver_email = os.getenv('RECEIVER_EMAIL')
        
        # Flight search parameters
        self.origin = "AUS"  # Austin
        self.destination = "SFO"  # San Francisco
        self.search_days = 14  # Next 2 weeks
        
        # Price tracking
        self.best_price = float('inf')
        self.best_flight_info = None
        self.price_history = []
        
        # Load previous best price if exists
        self.load_price_history()
        
    def load_price_history(self):
        """Load previous price history and best price"""
        try:
            if os.path.exists('price_history.json'):
                with open('price_history.json', 'r') as f:
                    self.price_history = json.load(f)
                    if self.price_history:
                        # Find the best price from history
                        best_entry = min(self.price_history, key=lambda x: x['price'])
                        self.best_price = best_entry['price']
                        self.best_flight_info = best_entry['flight_info']
                        logging.info(f"Loaded best price from history: ${self.best_price}")
        except Exception as e:
            logging.error(f"Error loading price history: {e}")
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def parse_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        # Remove currency symbols and commas, extract numbers
        price_match = re.search(r'[\d,]+', price_text)
        if price_match:
            return float(price_match.group().replace(',', ''))
        return float('inf')
    
    def search_google_flights(self, departure_date: str, return_date: str) -> Optional[Dict]:
        """Search Google Flights for round trip prices"""
        driver = None
        try:
            driver = self.setup_driver()
            
            # Format dates for URL (YYYY-MM-DD)
            dep_date = departure_date.replace('-', '')
            ret_date = return_date.replace('-', '')
            
            # Build Google Flights URL for round trip nonstop flights
            url = f"https://www.google.com/travel/flights/search?tfs=CBwQAhopEgoyMDI1LTAxLTEwagcIARIDQVVTcgcIARIDU0ZPGikSCjIwMjUtMDEtMTVqBwgBEgNTRk9yBwgBEgNBVVNwAYIBCwj___________8BQAFIAZgBAg&tfu=EgYIAhAAGAA"
            
            # Construct the actual URL with dates
            base_url = "https://www.google.com/travel/flights/search"
            params = f"?tfs=CBwQAhopag0IAhIJL20vMGZ6bWQSCjIwMjUtMDEtMTByDQgCEgkvbS8wZDZscBopag0IAhIJL20vMGQ2bHASCjIwMjUtMDEtMTVyDQgCEgkvbS8wZnptZHABggELCP___________wFAAUgBmAEC&hl=en"
            
            # Build URL with actual parameters
            url = f"https://www.google.com/travel/flights/booking?tfs=CBwQAhooEgoyMDI1LTAxLTEwag0IAhIJL20vMGZ6bWRyDQgCEgkvbS8wZDZscBooEgoyMDI1LTAxLTE1ag0IAhIJL20vMGQ2bHByDQgCEgkvbS8wZnptZHABggELCP___________wFAAUgBmAEB"
            
            # Simpler approach - use the search page
            url = f"https://www.google.com/travel/flights?q=Flights%20from%20{self.origin}%20to%20{self.destination}%20on%20{departure_date}%20through%20{return_date}%20nonstop%20only"
            
            logging.info(f"Searching flights: {departure_date} to {return_date}")
            driver.get(url)
            
            # Wait for page to load
            time.sleep(5)  # Initial wait for page load
            
            # Try to find and click on "Nonstop only" filter
            try:
                # Look for stops filter
                stops_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Stops')]"))
                )
                stops_button.click()
                time.sleep(1)
                
                # Click on "Nonstop only"
                nonstop_option = driver.find_element(By.XPATH, "//li[@role='option']//span[contains(text(), 'Nonstop only')]")
                nonstop_option.click()
                time.sleep(3)
            except:
                logging.warning("Could not apply nonstop filter")
            
            # Wait for results to load
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listitem']"))
                )
            except TimeoutException:
                logging.warning("No flights found or page didn't load properly")
                return None
            
            # Extract flight information
            flight_results = []
            
            # Find all flight cards
            flight_elements = driver.find_elements(By.CSS_SELECTOR, "[role='listitem']")
            
            for flight in flight_elements[:5]:  # Check first 5 results
                try:
                    # Extract price
                    price_element = flight.find_element(By.CSS_SELECTOR, "span[aria-label*='dollars']")
                    price_text = price_element.text
                    price = self.parse_price(price_text)
                    
                    # Extract flight details
                    try:
                        # Get departure and arrival times
                        time_elements = flight.find_elements(By.CSS_SELECTOR, "span[aria-label*='Departure time']")
                        if not time_elements:
                            time_elements = flight.find_elements(By.CSS_SELECTOR, "div[class*='time']")
                        
                        # Get airline
                        airline_element = flight.find_element(By.CSS_SELECTOR, "span[class*='airline']")
                        airline = airline_element.text if airline_element else "Unknown"
                        
                        # Get duration
                        duration_element = flight.find_element(By.CSS_SELECTOR, "div[aria-label*='Total duration']")
                        duration = duration_element.text if duration_element else "Unknown"
                        
                    except:
                        airline = "Unknown"
                        duration = "Unknown"
                    
                    flight_results.append({
                        'price': price,
                        'airline': airline,
                        'duration': duration,
                        'departure_date': departure_date,
                        'return_date': return_date
                    })
                    
                except Exception as e:
                    logging.debug(f"Error parsing flight element: {e}")
                    continue
            
            if flight_results:
                # Return the cheapest flight
                best_flight = min(flight_results, key=lambda x: x['price'])
                return best_flight
            
            return None
            
        except Exception as e:
            logging.error(f"Error in search_google_flights: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def search_kayak(self, departure_date: str, return_date: str) -> Optional[Dict]:
        """Alternative: Search on Kayak"""
        driver = None
        try:
            driver = self.setup_driver()
            
            # Format dates for Kayak (YYYY-MM-DD)
            url = f"https://www.kayak.com/flights/{self.origin}-{self.destination}/{departure_date}/{return_date}?sort=price_a&stops=0"
            
            logging.info(f"Searching Kayak: {departure_date} to {return_date}")
            driver.get(url)
            
            # Wait for results
            time.sleep(10)  # Kayak takes time to load
            
            # Check for captcha or blocking
            if "security check" in driver.page_source.lower():
                logging.warning("Kayak security check detected")
                return None
            
            try:
                # Wait for price elements
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='price-text']"))
                )
                
                # Find the best price
                price_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='price-text']")
                
                if price_elements:
                    prices = []
                    for elem in price_elements[:5]:
                        try:
                            price = self.parse_price(elem.text)
                            if price < float('inf'):
                                prices.append(price)
                        except:
                            continue
                    
                    if prices:
                        best_price = min(prices)
                        return {
                            'price': best_price,
                            'airline': 'Multiple',
                            'duration': 'Check website',
                            'departure_date': departure_date,
                            'return_date': return_date,
                            'source': 'Kayak'
                        }
                
            except TimeoutException:
                logging.warning("Kayak results timeout")
                
        except Exception as e:
            logging.error(f"Error in search_kayak: {e}")
        finally:
            if driver:
                driver.quit()
        
        return None
    
    def check_all_dates(self) -> Optional[Dict]:
        """Check flights for all date combinations in the next 2 weeks"""
        best_flight = None
        best_price = float('inf')
        
        # Generate date combinations
        today = datetime.now()
        
        for dep_days in range(1, self.search_days + 1):
            departure_date = (today + timedelta(days=dep_days)).strftime('%Y-%m-%d')
            
            # Try different trip lengths (2-7 days)
            for trip_length in range(2, 8):
                return_date = (today + timedelta(days=dep_days + trip_length)).strftime('%Y-%m-%d')
                
                # Try Google Flights first
                flight_info = self.search_google_flights(departure_date, return_date)
                
                # If Google Flights fails, try Kayak
                if not flight_info:
                    flight_info = self.search_kayak(departure_date, return_date)
                
                if flight_info and flight_info['price'] < best_price:
                    best_price = flight_info['price']
                    best_flight = flight_info
                
                # Add delay to avoid being blocked
                time.sleep(3)
        
        return best_flight
    
    def send_email_notification(self, flight_info: Dict):
        """Send email notification about better price"""
        subject = f"✈️ Better Flight Price Found! AUS → SFO: ${flight_info['price']:.2f}"
        
        body = f"""
        Great news! I found a better price for your round trip from Austin to San Francisco!
        
        🎯 Total Price: ${flight_info['price']:.2f}
        💰 Savings: ${self.best_price - flight_info['price']:.2f}
        
        ✈️ FLIGHT DETAILS:
        Departure Date: {flight_info['departure_date']}
        Return Date: {flight_info['return_date']}
        Airline: {flight_info.get('airline', 'Check website')}
        Duration: {flight_info.get('duration', 'Check website')}
        Source: {flight_info.get('source', 'Google Flights')}
        
        Trip Length: {(datetime.strptime(flight_info['return_date'], '%Y-%m-%d') - 
                       datetime.strptime(flight_info['departure_date'], '%Y-%m-%d')).days} days
        
        🔗 Quick Links:
        Google Flights: https://www.google.com/travel/flights?q=Flights%20from%20AUS%20to%20SFO%20on%20{flight_info['departure_date']}%20through%20{flight_info['return_date']}
        Kayak: https://www.kayak.com/flights/AUS-SFO/{flight_info['departure_date']}/{flight_info['return_date']}
        
        Book now before the price changes!
        
        Note: This is a scraped price. Please verify on the website before booking.
        """
        
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server

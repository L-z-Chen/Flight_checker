import requests
import json
import time
import os
import smtplib
import ssl
from datetime import date, timedelta

# --- ⚙️ CONFIGURATION - LOAD FROM FILE ⚙️ ---

def load_config():
    """Load configuration from config.txt file."""
    config = {}
    try:
        with open('config.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
        return config
    except FileNotFoundError:
        print("❌ config.txt file not found! Please create it with your credentials.")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

# Load configuration
config = load_config()
if not config:
    print("Stopping script due to configuration error.")
    exit(1)

# Amadeus API Credentials
AMADEUS_API_KEY = config.get('AMADEUS_API_KEY')
AMADEUS_API_SECRET = config.get('AMADEUS_API_SECRET')

# Email Notification Settings
SENDER_EMAIL = config.get('SENDER_EMAIL')
RECEIVER_EMAIL = config.get('RECEIVER_EMAIL')
EMAIL_APP_PASSWORD = config.get('EMAIL_APP_PASSWORD')

# Flight Search Parameters
ORIGIN_CITY_CODE = "AUS" # Austin
DESTINATION_CITY_CODE = "SFO" # San Francisco
TRIP_DURATION_DAYS = 14 # <--- UPDATED: Set to a fixed 2-week stay
SEARCH_WITHIN_DAYS = 14 # Search for flights departing in the next 14 days

# Script Settings
CHECK_INTERVAL_SECONDS = 3600 # Check once per hour (3600 seconds)
BEST_PRICE_FILE = "best_price.json"

# --- END OF CONFIGURATION ---


def get_amadeus_access_token(api_key, api_secret):
    """Get an access token from the Amadeus API."""
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": api_secret,
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        print("✅ Access token retrieved successfully.")
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get Amadeus access token: {e}")
        return None

def find_cheapest_flight(token, origin, destination, start_date, end_date, trip_duration):
    """Search for the cheapest nonstop flight for a fixed trip duration."""
    cheapest_flight = None
    
    current_date = start_date
    while current_date <= end_date:
        departure_date = current_date.strftime("%Y-%m-%d")
        return_date = (current_date + timedelta(days=trip_duration)).strftime("%Y-%m-%d")

        print(f"🔎 Searching: {origin} -> {destination} from {departure_date} to {return_date} ({trip_duration}-day trip)")

        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": 1,
            "nonStop": "true",
            "currencyCode": "USD",
            "max": 5, # We only need a few results to find the cheapest
        }
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 400: # Often means no flights found
                current_date += timedelta(days=1)
                continue
            response.raise_for_status()
            offers = response.json().get("data", [])
            
            if not offers:
                current_date += timedelta(days=1)
                continue

            # Find the cheapest offer in this batch
            current_best_offer = min(offers, key=lambda x: float(x["price"]["total"]))
            current_price = float(current_best_offer["price"]["total"])

            if cheapest_flight is None or current_price < cheapest_flight["price"]:
                cheapest_flight = {
                    "price": current_price,
                    "departure_date": departure_date,
                    "return_date": return_date,
                    "link": f"https://www.google.com/flights?hl=en#flt={origin}.{destination}.{departure_date}*{destination}.{origin}.{return_date}"
                }
                print(f"✨ New best price found in this search: ${current_price:.2f}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ API request failed for dates {departure_date} to {return_date}: {e}")
        
        time.sleep(0.3) # Short delay to respect API rate limits

        current_date += timedelta(days=1)

    return cheapest_flight

def send_email_notification(flight_info):
    """Send an email with the new cheapest flight details."""
    subject = f"New Cheapest Flight to {DESTINATION_CITY_CODE}! Only ${flight_info['price']:.2f}"
    body = f"""
    A new cheapest flight has been found!

    Destination: {ORIGIN_CITY_CODE} to {DESTINATION_CITY_CODE}
    Price: ${flight_info['price']:.2f}
    Departure Date: {flight_info['departure_date']}
    Return Date: {flight_info['return_date']}

    Book now on Google Flights:
    {flight_info['link']}
    """
    message = f"Subject: {subject}\n\n{body}"

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, EMAIL_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message)
        print(f"Email notification sent successfully to {RECEIVER_EMAIL}!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def load_best_price():
    """Load the best price found so far from a file."""
    if os.path.exists(BEST_PRICE_FILE):
        with open(BEST_PRICE_FILE, "r") as f:
            return json.load(f)
    return {"price": float('inf')} # Initialize with a very high price

def save_best_price(flight_info):
    """Save the new best price to a file."""
    with open(BEST_PRICE_FILE, "w") as f:
        json.dump(flight_info, f)


def main():
    """Main function to run the flight checker loop."""
    print("🚀 Starting Flight Price Checker...")
    access_token = get_amadeus_access_token(AMADEUS_API_KEY, AMADEUS_API_SECRET)
    if not access_token:
        print("Stopping script due to authentication failure.")
        return

    while True:
        print("\n" + "="*50)
        print(f"Running new check at {time.ctime()}")
        
        all_time_best = load_best_price()
        print(f"Current all-time best price: ${all_time_best['price']:.2f}")

        search_start_date = date.today() + timedelta(days=1)
        search_end_date = date.today() + timedelta(days=SEARCH_WITHIN_DAYS)

        current_cheapest = find_cheapest_flight(
            access_token,
            ORIGIN_CITY_CODE,
            DESTINATION_CITY_CODE,
            search_start_date,
            search_end_date,
            TRIP_DURATION_DAYS
        )

        if current_cheapest and current_cheapest["price"] < all_time_best["price"]:
            print("🎉🎉🎉 NEW ALL-TIME BEST PRICE FOUND! 🎉🎉🎉")
            print(f"Price: ${current_cheapest['price']:.2f}, Dates: {current_cheapest['departure_date']} to {current_cheapest['return_date']}")
            save_best_price(current_cheapest)
            send_email_notification(current_cheapest)
        elif current_cheapest:
            print(f"✅ Search complete. The cheapest price found this round was ${current_cheapest['price']:.2f}. Not better than the all-time best.")
        else:
            print("🤷 No flights found in the given date range for this check.")

        print(f"Waiting for {CHECK_INTERVAL_SECONDS / 60:.0f} minutes until the next check...")
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
# Flight Price Tracker 🛫

An automated Python script that continuously monitors flight prices between two cities using the Amadeus API. The script searches for the cheapest nonstop flights for a fixed 2-week trip duration and sends email notifications when new all-time best prices are found.

## Features ✨

- **Automated Price Monitoring**: Continuously checks flight prices every hour
- **Fixed Trip Duration**: Optimized for 2-week trips (14 days)
- **Nonstop Flights Only**: Filters for direct flights only
- **Email Notifications**: Sends alerts when new best prices are found
- **Price History**: Tracks and remembers the best price found so far
- **Google Flights Integration**: Provides direct booking links
- **Secure Configuration**: Credentials stored in separate config file

## Prerequisites 📋

- Python 3.6 or higher
- Amadeus API credentials (free test account available)
- Gmail account with App Password for email notifications
- Required Python packages (see Installation section)

## Installation 🚀

1. **Clone or download the project files**

2. **Install required dependencies**:
   ```bash
   pip install requests
   ```

3. **Set up your configuration**:
   - Create a `config.txt` file in the project directory
   - Add your credentials in the following format:
   ```
   # Amadeus API Credentials
   AMADEUS_API_KEY=your_api_key_here
   AMADEUS_API_SECRET=your_api_secret_here

   # Email Notification Settings
   SENDER_EMAIL=your_email@gmail.com
   RECEIVER_EMAIL=your_email@gmail.com
   EMAIL_APP_PASSWORD=your_gmail_app_password
   ```

## Configuration 🔧

### Required Credentials

#### Amadeus API Setup
1. Visit [Amadeus for Developers](https://developers.amadeus.com/)
2. Create a free account
3. Generate API credentials (API Key and Secret)
4. Add them to your `config.txt` file

#### Gmail App Password Setup
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
3. Use this App Password in your `config.txt` file (NOT your regular Gmail password)

### Customizable Parameters

In `weeks.py`, you can modify these settings:

```python
# Flight Search Parameters
ORIGIN_CITY_CODE = "AUS"           # Your departure city (Austin)
DESTINATION_CITY_CODE = "SFO"      # Your destination city (San Francisco)
TRIP_DURATION_DAYS = 14            # Fixed trip duration (14 days)
SEARCH_WITHIN_DAYS = 14            # Search window (next 14 days)

# Script Settings
CHECK_INTERVAL_SECONDS = 3600      # Check frequency (1 hour)
```

## Usage 🎯

1. **Ensure your `config.txt` file is properly set up**

2. **Run the script**:
   ```bash
   python weeks.py
   ```

3. **The script will**:
   - Load your configuration
   - Authenticate with Amadeus API
   - Start monitoring flight prices every hour
   - Display search progress in the console
   - Send email notifications for new best prices

## How It Works 🔍

### Search Algorithm
1. **Date Range**: Searches for flights departing in the next 14 days
2. **Trip Duration**: Looks for exactly 14-day round trips
3. **Flight Type**: Filters for nonstop flights only
4. **Price Tracking**: Compares current prices with the best price found so far
5. **Notifications**: Sends email alerts when new all-time best prices are discovered

### API Integration
- Uses Amadeus Flight Offers Search API v2
- Implements proper rate limiting (0.3 second delays between requests)
- Handles API errors gracefully
- Uses OAuth2 authentication

### Data Persistence
- Saves best prices to `best_price.json`
- Maintains price history across script restarts
- Initializes with infinite price if no previous data exists

## File Structure 📁

```
flight_tracker/
├── weeks.py              # Main script
├── config.txt            # Configuration file (create this)
├── best_price.json       # Price history (auto-generated)
└── README.md            # This file
```

## Security Notes 🔒

- **Never commit `config.txt` to version control**
- Add `config.txt` to your `.gitignore` file
- Keep your API credentials and email passwords secure
- The script uses Gmail's App Password system for enhanced security

## Troubleshooting 🛠️

### Common Issues

1. **"config.txt file not found"**
   - Ensure `config.txt` exists in the same directory as `weeks.py`
   - Check file permissions

2. **"Failed to get Amadeus access token"**
   - Verify your API credentials in `config.txt`
   - Check your internet connection
   - Ensure you're using the correct API endpoint (test vs production)

3. **"Failed to send email"**
   - Verify your Gmail App Password
   - Ensure 2-Factor Authentication is enabled
   - Check that you're using the App Password, not your regular password

4. **No flights found**
   - Check that your city codes are valid (e.g., "AUS" for Austin)
   - Verify there are nonstop flights between your cities
   - Try adjusting the search window or trip duration

### API Rate Limits
- The script includes built-in rate limiting (0.3 seconds between requests)
- Amadeus test API has generous limits for development
- For production use, consider upgrading to a paid Amadeus account

## Customization Options 🎨

### Changing Cities
Update the city codes in `weeks.py`:
```python
ORIGIN_CITY_CODE = "LAX"      # Los Angeles
DESTINATION_CITY_CODE = "JFK"  # New York
```

### Adjusting Search Parameters
```python
TRIP_DURATION_DAYS = 7        # 1-week trips
SEARCH_WITHIN_DAYS = 30       # Search next 30 days
CHECK_INTERVAL_SECONDS = 1800 # Check every 30 minutes
```

### Modifying Email Content
Edit the `send_email_notification()` function to customize email format and content.

## Contributing 🤝

Feel free to submit issues, feature requests, or pull requests to improve this flight tracker!

## License 📄

This project is open source and available under the MIT License.

---

**Happy Flight Hunting! ✈️** 
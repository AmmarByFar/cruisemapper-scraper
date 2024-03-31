# Cruise Ship Itinerary Scraper

This Python script scrapes cruise ship itinerary data from the website [https://www.cruisemapper.com](https://www.cruisemapper.com) and stores the information in a CSV file. It allows you to retrieve detailed itinerary information for various cruise ships, including ports visited, dates, times, passenger and crew counts, and more.

## Features

- Scrapes itinerary data for cruise ships from [https://www.cruisemapper.com](https://www.cruisemapper.com)
- Handles pagination to scrape data from multiple pages
- Extracts detailed information such as cruise line, ship name, ports, dates, times, passenger and crew counts
- Fills in missing "At Sea" days in the itinerary
- Avoids processing duplicate itineraries based on itinerary ID and ship name
- Provides an option to remove duplicate records based on port and date
- Allows customization of the delay time between requests to avoid rate limiting
- Handles keyboard interrupts gracefully and cleans up before exiting
- Logs important information and errors for debugging and monitoring

## Prerequisites

- Python 3.x
- Required Python packages: `requests`, `beautifulsoup4`

## Installation

1. Clone the repository or download the script file.

2. Install the required Python packages by running the following command:

pip install requests beautifulsoup4

## Usage

1. Open a terminal or command prompt and navigate to the directory where the script is located.

2. Run the script using the following command:

python scrape.py [--remove-duplicates] [--delay-time DELAY_TIME]

- `--remove-duplicates` (optional): If specified, the script will remove duplicate records from the generated CSV file based on port and date.
- `--delay-time DELAY_TIME` (optional): Specifies the delay time in seconds between requests to avoid rate limiting. Default is 0.7 seconds.

3. The script will start scraping the cruise ship itinerary data from [https://www.cruisemapper.com](https://www.cruisemapper.com) and save the information in a file named `itineraries.csv`.

4. If the `--remove-duplicates` flag is used, the script will remove duplicate records from the CSV file based on port and date and save the unique records in a new file named `itineraries_without_duplicates.csv`.

5. The script will log important information and errors during the scraping process.

6. If the script is interrupted using the keyboard (Ctrl+C), it will clean up and exit gracefully.

## Output

The script generates a CSV file named `itineraries.csv` containing the scraped cruise ship itinerary data. The CSV file has the following columns:
- Itinerary ID
- Cruise Line
- Ship Name
- Date
- Time
- Port
- Max Passengers
- Crew

If the `--remove-duplicates` flag is used, the script will also generate a file named `itineraries_without_duplicates.csv` containing the unique records without duplicates.

## Disclaimer

Please note that web scraping may be subject to legal restrictions and the terms of service of the website being scraped. Make sure to review and comply with the website's robots.txt file and any applicable legal requirements before using this script. Use it responsibly and at your own risk.
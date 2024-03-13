import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import math
import csv
import json
import re

def parse_date_time(date_time_text, year):
    # Define the regular expressions for the different date formats
    date_time_regexes = [
        (r"(\d{1,2} \w{3}) (\d{2}:\d{2})", "%d %b %H:%M"),  # 25 Jul 17:00
        (r"(\d{1,2} \w{3}) (\d{2}:\d{2}) - (\d{2}:\d{2})", "%d %b %H:%M"),  # 26 Jul 07:00 - 17:00
        (r"(\d{1,2} \w{3}) - (\d{1,2} \w{3})", "%d %b"),  # 27 Jul - 28 Jul
        (r"(\d{1,2} \w{3} \d{2}:\d{2}) - (\d{1,2} \w{3} \d{2}:\d{2})", "%d %b %H:%M"),  # 30 Jul 14:30 - 31 Jul 17:00
        (r"(\d{1,2} \w{3})", "%d %b")  # 21 Jul
    ]

    # Try each regex until one matches
    for regex, date_format in date_time_regexes:
        match = re.match(regex, date_time_text)
        if match:
            # If a match is found, parse the date and time
            date_str = match.group(1)
            date = datetime.strptime(f"{date_str} {year}", f"{date_format} %Y")
            date = date.strftime('%Y-%m-%d')

            # If there is a second group, it is the time
            if match.lastindex >= 2:
                time_str = match.group(2)
            else:
                time_str = "Unknown"

            return date, time_str

    # If no regex matches, the date and time are unknown
    return "Unknown", "Unknown"

# Set up logging
logging.basicConfig(level=logging.INFO)

base_url = "https://www.cruisemapper.com/ships?page="
start_page = 1

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

# Get the total number of ships and calculate the end page
response = requests.get(base_url + str(start_page), headers=headers)
soup = BeautifulSoup(response.text, "html.parser")
total_ships = int(soup.find("span", class_="total").text.split()[0])
print(f"Total ships: {total_ships}")
ships_per_page = 15
end_page = math.ceil(total_ships / ships_per_page)

# Open the CSV file
with open('itineraries.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    # Write the header
    writer.writerow(["Cruise Line", "Ship Name", "Date", "Time", "Port"])

    for page in range(start_page, end_page + 1):
        url = base_url + str(page)
        logging.info(f"Making request to: {url}")
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            logging.info("Request successful, received data.")
        else:
            logging.warning(f"Request failed, status code: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        ship_list = soup.find_all("li", class_="col-sm-6")

        for ship in ship_list:
            ship_name = ship.find("h3").text.strip()
            ship_url = ship.find("a", href=True)["href"]
            print(f"Scraping itinerary for ship: {ship_name}")
            print(f"URL: {ship_url}")

            if "/ships/" in ship_url:
                # Visit each ship's URL and save the itinerary data
                time.sleep(7)  # Delay between requests to avoid rate limiting
                ship_response = requests.get(ship_url, headers=headers)
                ship_soup = BeautifulSoup(ship_response.text, "html.parser")
                cruise_line = ship_soup.find("a", class_="shipCompanyLink").text.strip()  # Extract the cruise line
                print(f"Cruise Line: {cruise_line}")
                itinerary_rows = ship_soup.find_all("tr", {"data-row": True})

                for row in itinerary_rows:
                    id_number = row["data-row"]
                     # Extract the year from the 'cruiseDatetime' class
                    year = row.find("td", class_="cruiseDatetime").text.split()[0]
                    time.sleep(7)  # Delay between requests to avoid rate limiting
                    cruise_url = f"https://www.cruisemapper.com/ships/cruise.json?id={id_number}"
                    ajax_headers = headers.copy()  # Create a copy of the headers
                    ajax_headers["X-Requested-With"] = "XMLHttpRequest"  # Add the additional header
                    print(f"Scraping itinerary for cruise: {id_number}")
                    print(f"URL: {cruise_url}")
                    cruise_response = requests.get(cruise_url, headers=ajax_headers)  # Use the updated headers
                    cruise_data = json.loads(cruise_response.text)
                    cruise_soup = BeautifulSoup(cruise_data["result"], "html.parser")
                    date_times = cruise_soup.find_all("td", class_="date")
                    ports = cruise_soup.find_all("td", class_="text")

                    for date_time, port in zip(date_times, ports):
                        date, time_str = parse_date_time(date_time.text, year)
                        writer.writerow([cruise_line, ship_name, date, time_str, port.text.strip()])  # Use the extracted cruise line
                        print(f"Date: {date}, Time: {time_str}, Port: {port.text.strip()}")
                        print("Data saved to CSV file.")

                    # for date_time, port in zip(date_times, ports):
                    #     date_time_parts = date_time.text.split()
                    #     if len(date_time_parts) == 2:
                    #         # If there are two parts, the first is the date and the second is the time
                    #         date, time_str = date_time_parts
                    #         # Parse the date into a datetime object
                    #         date = datetime.strptime(f"{date} {year}", "%b %d %Y")  # Adjust the format string as needed
                    #         # Format the datetime object in ISO 8601 format
                    #         date = date.strftime('%Y-%m-%d')
                    #     elif len(date_time_parts) == 1:
                    #         # If there is only one part, it is the date and the time is unknown
                    #         date = datetime.strptime(f"{date_time_parts[0]} {year}", "%b %Y")
                    #         date = date.strftime('%Y-%m-%d')
                    #         time_str = "Unknown"
                    #     else:
                    #         # If there are no parts, both the date and time are unknown
                    #         date = "Unknown"
                    #         time_str = "Unknown"
                    #     writer.writerow([cruise_line, ship_name, date, time_str, port.text.strip()])  # Use the extracted cruise line
                    #     print(f"Date: {date}, Time: {time_str}, Port: {port.text.strip()}")
                    #     print("Data saved to CSV file.")

        # Delay between requests to avoid rate limiting
        time.sleep(7)  # Adjust the delay as needed
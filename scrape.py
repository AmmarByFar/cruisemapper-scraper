import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import logging
import math
import csv
import json
import re
import os

# Define the delay time in seconds
delay_time = 0.6

try:
    with open('processed_ships.txt', 'r') as file:
        processed_ships = [line.strip() for line in file]
except FileNotFoundError:
    processed_ships = []

def parse_date_time(date_time_text, year):
    # Define the regular expressions for the different date formats
    date_time_regexes = [
        (r"(\d{1,2} \w{3}) (\d{2}:\d{2}) - (\d{2}:\d{2})", "%d %b %H:%M"),  # 26 Jul 07:00 - 17:00
        (r"(\d{1,2} \w{3} \d{2}:\d{2}) - (\d{1,2} \w{3} \d{2}:\d{2})", "%d %b %H:%M"),  # 30 Jul 14:30 - 31 Jul 17:00
        (r"(\d{1,2} \w{3}) (\d{2}:\d{2})", "%d %b %H:%M"),  # 25 Jul 17:00
        (r"(\d{1,2} \w{3}) - (\d{1,2} \w{3})", "%d %b"),  # 27 Jul - 28 Jul
        (r"(\d{1,2} \w{3})", "%d %b")  # 21 Jul
    ]

    # Try each regex until one matches
    for regex, date_format in date_time_regexes:
        match = re.match(regex, date_time_text)
        if match:
            # If a match is found, parse the date and time
            date_str = match.group(1)
            try:
                date = datetime.strptime(f"{date_str} {year}", f"{date_format} %Y")
            except ValueError:
                date_format = "%d %b"
                date = datetime.strptime(f"{date_str} {year}", f"{date_format} %Y")
            date = date.strftime('%Y-%m-%d')

            # If there is a second group, it is the time
            if match.lastindex >= 2:
                time_str = match.group(2)
                if match.lastindex >= 3:
                    time_str += " - " + match.group(3)
            else:
                time_str = ""

            return date, time_str

    # If no regex matches, the date and time are unknown
    return "", ""

def handle_response(response):
    if response.status_code == 200:
        logging.info("Request successful, received data.")
    elif response.status_code == 429 or response.status_code == 503:
        logging.error("Request failed due to rate limiting.")
        raise Exception("Rate limit exceeded.")
    else:
        logging.warning(f"Request failed, status code: {response.status_code}")

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

# Check if the file exists and is non-empty
if not os.path.isfile('itineraries.csv') or os.stat('itineraries.csv').st_size == 0:
    # Open the CSV file in write mode to write the header
    with open('itineraries.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Cruise Line", "Ship Name", "Date", "Time", "Port", "Max Passengers", "Crew"])

with open('itineraries.csv', 'a', newline='') as file:
    writer = csv.writer(file)

    for page in range(start_page, end_page + 1):
        url = base_url + str(page)
        logging.info(f"Making request to: {url}")
        response = requests.get(url, headers=headers)
        handle_response(response)

        if response.status_code == 200:
            logging.info("Request successful, received data.")
        else:
            logging.warning(f"Request failed, status code: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        ship_list = soup.find_all("li", class_="col-sm-6")

        for ship in ship_list:
            ship_name = ship.find("h3").text.strip()

            # If the ship has been processed before, skip it
            if ship_name in processed_ships:
                print(f"Ship {ship_name} has already been processed, skipping.")
                continue

            ship_url = ship.find("a", href=True)["href"]
            print(f"Scraping itinerary for ship: {ship_name}")
            print(f"URL: {ship_url}")

            if "/ships/" in ship_url:
                # Visit each ship's URL and save the itinerary data
                time.sleep(delay_time)  # Delay between requests to avoid rate limiting
                ship_response = requests.get(ship_url, headers=headers)
                handle_response(ship_response)
                ship_soup = BeautifulSoup(ship_response.text, "html.parser")

                # Extract the maximum passengers and crew numbers
                max_passengers = None
                crew = None
                table_rows = ship_soup.find_all("tr")
                for row in table_rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        try:
                            if cells[0].text == "Passengers":
                                # If the passengers number is a range, take the maximum number
                                numbers = re.findall(r'\d+', cells[1].text)
                                if numbers:
                                    max_passengers = max(map(int, numbers))
                                else:
                                    max_passengers = ""
                            elif cells[0].text == "Crew":
                                crew = int(cells[1].text)
                        except ValueError:
                            # If the conversion to int fails, replace with an empty string
                            if cells[0].text == "Passengers":
                                max_passengers = ""
                            elif cells[0].text == "Crew":
                                crew = ""

                cruise_line = ship_soup.find("a", class_="shipCompanyLink").text.strip()  # Extract the cruise line
                print(f"Cruise Line: {cruise_line}")
                itinerary_rows = ship_soup.find_all("tr", {"data-row": True})

                for row in itinerary_rows:
                    id_number = row["data-row"]
                     # Extract the year from the 'cruiseDatetime' class
                    year = int(row.find("td", class_="cruiseDatetime").text.split()[0])
                    time.sleep(delay_time)  # Delay between requests to avoid rate limiting
                    cruise_url = f"https://www.cruisemapper.com/ships/cruise.json?id={id_number}"
                    ajax_headers = headers.copy()  
                    ajax_headers["X-Requested-With"] = "XMLHttpRequest"  
                    print(f"Scraping itinerary for cruise: {id_number}")
                    print(f"URL: {cruise_url}")
                    cruise_response = requests.get(cruise_url, headers=ajax_headers)  
                    handle_response(cruise_response)
                    cruise_data = json.loads(cruise_response.text)
                    cruise_soup = BeautifulSoup(cruise_data["result"], "html.parser")
                    date_times = cruise_soup.find_all("td", class_="date")
                    ports = cruise_soup.find_all("td", class_="text")

                    prev_month = None
                    for date_time, port in zip(date_times, ports):
                        date, time_str = parse_date_time(date_time.text, year)
                        month = datetime.strptime(date, '%Y-%m-%d').month
                        if prev_month == 12 and month == 1:
                            year += 1
                        prev_month = month
                        port_text = port.text.strip()
                        port_text = port_text.replace("Arriving in ", "")
                        port_text = port_text.replace(" hotels", "")
                        port_text = port_text.replace("Departing from ", "")
                        writer.writerow([cruise_line, ship_name, date, time_str, port_text, max_passengers, crew])
                        print(f"Date: {date}, Time: {time_str}, Port: {port_text}")

                # After processing the ship, add it to the list of processed ships
                processed_ships.append(ship_name)

                # And save the updated list to the file
                with open('processed_ships.txt', 'a') as file:
                    file.write(ship_name + '\n')

        # Delay between requests to avoid rate limiting
        time.sleep(delay_time) 
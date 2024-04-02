import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import logging
import math
import csv
import json
import re
import os
import argparse
import atexit

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

parser = argparse.ArgumentParser(description='Scrape cruise ship itineraries.')
parser.add_argument('--remove-duplicates', action='store_true', help='Remove duplicate records based on port and date')
parser.add_argument('--delay-time', type=float, default=0.7, help='Delay time between requests in seconds (default: 0.7)')
args = parser.parse_args()

# Set the delay time based on the command-line argument
delay_time = args.delay_time

def exit_handler():
    if args.remove_duplicates:
        logging.info("Removing duplicate records from CSV file.")
        remove_duplicates_from_csv('itineraries.csv')

atexit.register(exit_handler)

def remove_duplicates_from_csv(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # Store the header row
        rows = list(reader)

    unique_rows = []
    seen_records = set()

    for row in rows:
        record_key = (row[1], row[2], row[3], row[5])  # Create a unique key based on date and port
        if record_key not in seen_records:
            seen_records.add(record_key)
            unique_rows.append(row)
        else:
            logging.info(f"Duplicate record found for cruiseline {row[1]}, ship {row[2]} date {row[3]} and port {row[5]}, removing.")

    # Write the unique rows to a new CSV file with a different name
    new_csv_file = 'itineraries_without_duplicates.csv'
    with open(new_csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)  # Write the header row
        writer.writerows(unique_rows)  # Write the unique rows

    logging.info(f"Duplicates removed. Unique records written to {new_csv_file}.")

def fill_in_dates(start_date, end_date):
    # Create a list of all dates from the start to the end
    all_dates = [start_date + timedelta(days=x) for x in range((end_date-start_date).days + 1)]
    return all_dates

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
                start_date = datetime.strptime(f"{date_str} {year}", f"{date_format} %Y")
            except ValueError:
                try:
                    start_date = datetime.strptime(f"{date_str} {year+1}", f"{date_format} %Y")
                    year += 1
                except ValueError:
                    continue

            # If there is a second group, it is the end date
            end_date = start_date
            if match.lastindex >= 2:
                end_date_str = match.group(2)
                try:
                    end_date = datetime.strptime(f"{end_date_str} {year}", f"{date_format} %Y")
                except ValueError:
                    try:
                        end_date = datetime.strptime(f"{end_date_str} {year+1}", f"{date_format} %Y")
                        year += 1
                    except ValueError:
                        continue

            # Generate a list of dates from start_date to end_date
            date = start_date
            dates = []
            while date <= end_date:
                dates.append(date.strftime('%Y-%m-%d'))
                date += timedelta(days=1)

           # Set the time string based on the matched regex
            time_str = ""
            time_regex = r"(\d{2}:\d{2})(?:\s*-\s*(\d{2}:\d{2}))?"
            time_match = re.search(time_regex, date_time_text)
            if time_match:
                if time_match.group(2):
                    time_str = f"{time_match.group(1)} - {time_match.group(2)}"
                else:
                    time_str = time_match.group(1)

            return dates, time_str, year

    return [], "", year

def handle_response(response):
    if response.status_code == 200:
        logging.info("Request successful, received data.")
    elif response.status_code == 429 or response.status_code == 503:
        logging.error("Request failed due to rate limiting.")
        raise Exception("Rate limit exceeded.")
    else:
        logging.warning(f"Request failed, status code: {response.status_code}")

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

processed_data = set()
try:
    with open('itineraries.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            itinerary_id, ship_name = row[0], row[2]
            processed_data.add((itinerary_id, ship_name))
except FileNotFoundError:
    pass

if not os.path.isfile('itineraries.csv') or os.stat('itineraries.csv').st_size == 0:
    with open('itineraries.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Itinerary Id","Cruise Line", "Ship Name", "Date", "Time", "Port", "Max Passengers", "Crew"])

if __name__ == '__main__':
    try:
        with open('itineraries.csv', 'a', newline='') as file:
            writer = csv.writer(file)

            for page in range(start_page, end_page + 1):
                url = base_url + str(page)
                logging.info(f"Making request to: {url}")
                response = requests.get(url, headers=headers)
                handle_response(response)

                if response.status_code == 200:
                    logging.info(f"Processing page {page} of {end_page}")
                else:
                    logging.warning(f"Request failed, status code: {response.status_code}")

                soup = BeautifulSoup(response.text, "html.parser")
                ship_list = soup.find_all("li", class_="col-sm-6")

                for ship in ship_list:
                    ship_name = ship.find("h3").text.strip()

                    ship_url = ship.find("a", href=True)["href"]
                    logging.info(f"Scraping itinerary for ship: {ship_name}")

                    if "/ships/" in ship_url:
                        try:
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
                                logging.info(f"Processing itinerary row {id_number}")

                                # Check if the current itinerary ID and ship name combination has already been processed
                                if (id_number, ship_name) in processed_data:
                                    logging.info(f"Itinerary {id_number} for ship {ship_name} has already been processed, skipping.")
                                    continue

                                # Extract the year from the 'cruiseDatetime' class
                                year = int(row.find("td", class_="cruiseDatetime").text.split()[0])
                                time.sleep(delay_time)
                                cruise_url = f"https://www.cruisemapper.com/ships/cruise.json?id={id_number}"
                                ajax_headers = headers.copy()  
                                ajax_headers["X-Requested-With"] = "XMLHttpRequest"  
                                cruise_response = requests.get(cruise_url, headers=ajax_headers)  
                                handle_response(cruise_response)
                                cruise_data = json.loads(cruise_response.text)
                                cruise_soup = BeautifulSoup(cruise_data["result"], "html.parser")
                                date_times = cruise_soup.find_all("td", class_="date")
                                ports = cruise_soup.find_all("td", class_="text")

                                prev_date = None
                                for date_time, port in zip(date_times, ports):
                                    dates, time_data, year = parse_date_time(date_time.text, year)
                                    for date in dates:
                                        if prev_date:
                                            days_diff = (datetime.strptime(date, '%Y-%m-%d') - prev_date).days
                                            if days_diff < 0:
                                                # If the date is earlier than the previous date, increment the year
                                                year += 1
                                                date = datetime.strptime(date, '%Y-%m-%d').replace(year=year).strftime('%Y-%m-%d')
                                            elif days_diff > 1:
                                                # Fill in the missing "At Sea" days
                                                gap_date = prev_date + timedelta(days=1)
                                                while gap_date < datetime.strptime(date, '%Y-%m-%d'):
                                                    writer.writerow([id_number, cruise_line, ship_name, gap_date.strftime('%Y-%m-%d'), "", "At Sea", max_passengers, crew])
                                                    gap_date += timedelta(days=1)

                                        port_text = port.text.strip()
                                        port_text = port_text.replace("Arriving in ", "")
                                        port_text = port_text.replace(" hotels", "")
                                        port_text = port_text.replace("Departing from ", "")
                                        port_text = port_text.rstrip()
                                        writer.writerow([id_number, cruise_line, ship_name, date, time_data, port_text, max_passengers, crew])
                                        logging.info(f"Wrote row for date {date} and port {port_text}")
                                        prev_date = datetime.strptime(date, '%Y-%m-%d')
                                # Add the processed itinerary ID and ship name combination to the set
                                processed_data.add((id_number, ship_name))

                            logging.info(f"Finished processing ship {ship_name}")
                        except Exception as e:
                            logging.error(f"An error occurred: {str(e)}")
                            raise

                time.sleep(delay_time)
                logging.info(f"Finished processing page {page}, sleeping for {delay_time} seconds")

        if(args.remove_duplicates):
            logging.info("Removing duplicate records from CSV file.")
            remove_duplicates_from_csv('itineraries.csv')

    except KeyboardInterrupt:
        logging.info("Script interrupted by keyboard. Removing duplicates...")
    finally:
        logging.info("Script finished.")
    
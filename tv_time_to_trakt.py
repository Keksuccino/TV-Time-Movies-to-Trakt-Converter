import requests
import re
import json
from tqdm import tqdm
import colorama
from colorama import Fore, Style
from datetime import datetime
import urllib.parse
import csv
import sys

# Initialize colorama (especially important on Windows)
colorama.init()

# We'll store a reusable set of headers with a common user-agent to help avoid 403 errors on IMDb
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/100.0.4896.60 Safari/537.36"
    )
}


def csv_to_json(csv_file_path, json_file_path):
    """
    Converts a CSV file to a JSON file. Assumes the first row of the CSV
    file contains column headers. Writes the resulting list of dicts to 'json_file_path'.
    """
    data_list = []
    try:
        with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                data_list.append(row)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file_path}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

    # Write to JSON file
    try:
        with open(json_file_path, mode='w', encoding='utf-8') as json_file:
            json.dump(data_list, json_file, indent=2, ensure_ascii=False)
        print(f"Success: CSV '{csv_file_path}' converted to '{json_file_path}'.")
    except IOError as e:
        print(f"Error writing to JSON file: {e}")
        sys.exit(1)


def get_first_imdb_id(page_source):
    """
    Given an HTML page source (as plain text), find the first occurrence
    of imdb_id":"tt#### (with or without escaped quotes) and return it (e.g., "tt0081505").
    If not found, return None.
    """
    pattern = r'\\"imdb_id\\":\\"(tt\d+)\\"|imdb_id":"(tt\d+)"'
    match = re.search(pattern, page_source)
    if match:
        return match.group(1) if match.group(1) else match.group(2)
    else:
        return None


def get_imdb_id_by_search(movie_name):
    """
    Fallback: search IMDb by the movie name.
    Returns the first 'tt####' ID found, or None if not found.
    """
    movie_name_encoded = urllib.parse.quote_plus(movie_name)
    search_url = f"https://www.imdb.com/find?q={movie_name_encoded}&s=tt"

    try:
        response = requests.get(search_url, timeout=10, headers=HEADERS)
        if response.status_code == 200:
            # Example snippet: /title/tt0372784/?ref_=fn_tt_tt_1
            pattern = r'/title/(tt\d+)/'
            match = re.search(pattern, response.text)
            if match:
                fallback_imdb_id = match.group(1)
                tqdm.write(
                    f"{Fore.BLUE}Finished movie '{movie_name}'! Obtained IMDb ID using movie name fallback, "
                    f"make sure to double-check later: {fallback_imdb_id}{Style.RESET_ALL}"
                )
                return fallback_imdb_id
            else:
                tqdm.write(f"{Fore.RED}No search results for '{movie_name}'{Style.RESET_ALL}")
                return None
        else:
            tqdm.write(
                f"{Fore.RED}Failed to retrieve IMDB search results for '{movie_name}' "
                f"(status code {response.status_code}){Style.RESET_ALL}"
            )
            return None
    except requests.RequestException as e:
        tqdm.write(
            f"{Fore.RED}Error while searching IMDB for '{movie_name}': {e}{Style.RESET_ALL}"
        )
        return None


def convert_created_at_to_watched_at(created_at_str):
    """
    Convert the 'created_at' timestamp (e.g., '2020-09-21 02:17:20')
    to the 'watched_at' format (e.g., '2024-01-12T02:00:00Z').
    """
    dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def add_imdb_ids_to_movies(input_file='metadata.json', output_file='import_data_for_trakt.json'):
    """
    Reads JSON, finds/fetches IMDb IDs, and writes final data to 'output_file'.
    Format of each output entry: {"id": "tt#####", "watched_at": "YYYY-MM-DDTHH:MM:SSZ"}
    """
    # Read the metadata JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total_entries = len(data)
    watched_movies = []

    # Keep track of movies that ended with no IMDb ID
    missing_imdb_ids = []
    # Keep track of any movies that were successfully handled by fallback
    fallback_obtained = []

    with tqdm(
        total=total_entries,
        desc=f"{Fore.MAGENTA}Processing entries{Style.RESET_ALL}",
        bar_format=f"{Fore.MAGENTA}{{l_bar}}{{bar}}{{r_bar}}{Style.RESET_ALL}",
        ncols=80
    ) as pbar:
        for entry in data:
            entity_type = entry.get('entity_type', '')
            uuid = entry.get('uuid', '')
            movie_name = entry.get('movie_name', '(no title)')
            type_uuid_n = entry.get('type-uuid-n', '')
            created_at = entry.get('created_at', '')

            # 1) Skip if it's not a movie
            if entity_type != 'movie':
                tqdm.write(
                    f"{Fore.LIGHTYELLOW_EX}Skipped non-movie entry '{movie_name}' "
                    f"(entity_type: {entity_type}, UUID: {uuid}){Style.RESET_ALL}"
                )
                pbar.update(1)
                continue

            # 2) Skip if 'type-uuid-n' does NOT start with "watch-"
            if not type_uuid_n.startswith("watch-"):
                tqdm.write(
                    f"{Fore.LIGHTYELLOW_EX}Skipped unwatched movie '{movie_name}' "
                    f"because type-uuid-n doesn't start with 'watch-' (UUID: {uuid}){Style.RESET_ALL}"
                )
                pbar.update(1)
                continue

            # Try fetching the IMDb ID from TVTime
            imdb_id = None
            url = f"https://www.tvtime.com/movie/{uuid}"
            try:
                response = requests.get(url, timeout=10, headers=HEADERS)
                if response.status_code == 200:
                    imdb_id = get_first_imdb_id(response.text)
                else:
                    tqdm.write(
                        f"{Fore.LIGHTYELLOW_EX}Failed to retrieve page for UUID: {uuid} "
                        f"(status code {response.status_code}){Style.RESET_ALL}"
                    )
            except requests.RequestException as e:
                tqdm.write(
                    f"{Fore.LIGHTYELLOW_EX}Error retrieving page for UUID: {uuid} -> {e}{Style.RESET_ALL}"
                )

            # If we couldn't find IMDb ID on TVTime, do fallback by searching IMDb
            tvtime_failed = (imdb_id is None)
            if not imdb_id:
                imdb_id = get_imdb_id_by_search(movie_name)

            if imdb_id:
                # If this was obtained by fallback (i.e. TVTime failed), store detailed info
                if tvtime_failed:
                    fallback_obtained.append({
                        "movie_name": movie_name,
                        "imdb_id": imdb_id,
                        "uuid": uuid
                    })

                watched_at = convert_created_at_to_watched_at(created_at)
                watched_movies.append({
                    "id": imdb_id,
                    "watched_at": watched_at
                })
                tqdm.write(
                    f"{Fore.LIGHTGREEN_EX}Finished movie '{movie_name}' (UUID: {uuid}){Style.RESET_ALL}"
                )
            else:
                # Store enough info to print in the same format
                missing_imdb_ids.append({
                    "movie_name": movie_name,
                    "uuid": uuid
                })
                tqdm.write(
                    f"{Fore.RED}Finished movie '{movie_name}' but no IMDb ID found (UUID: {uuid}){Style.RESET_ALL}"
                )

            pbar.update(1)

    # Print missing IDs if any (in the same style as fallback)
    if missing_imdb_ids:
        print("\nCould not find IMDb ID (even via fallback search) for these entries:")
        for item in missing_imdb_ids:
            print(
                f"  {item['movie_name']} => no_id => https://www.tvtime.com/movie/{item['uuid']}"
            )

    # Also print fallback successes, now including IMDb link
    if fallback_obtained:
        print("\nMovies where the IMDb ID was successfully obtained via search fallback:")
        for item in fallback_obtained:
            print(
                f"  {item['movie_name']} => {item['imdb_id']} => "
                f"https://www.tvtime.com/movie/{item['uuid']} => "
                f"https://www.imdb.com/title/{item['imdb_id']}"
            )

    # Save only the watched-movies data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(watched_movies, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {len(watched_movies)} watched movies to '{output_file}'.")


def main():
    """
    1. Convert the CSV file ('tracking-prod-records.csv') to a temporary JSON ('temp_metadata.json').
    2. Process that JSON to gather IMDb IDs.
    3. Write the final output to 'import_data_for_trakt.json'.
    """
    csv_file = "tracking-prod-records.csv"
    temp_json_file = "temp_metadata.json"
    final_output_file = "import_data_for_trakt.json"

    # 1) Convert CSV -> JSON
    csv_to_json(csv_file_path=csv_file, json_file_path=temp_json_file)

    # 2) Process the JSON and output final
    add_imdb_ids_to_movies(
        input_file=temp_json_file,
        output_file=final_output_file
    )


if __name__ == '__main__':
    main()

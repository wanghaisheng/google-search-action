import sys
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
import re
import json

# Define a user-agent to mimic a real browser visit
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- NEW HELPER FUNCTIONS (INTEGRATED) ---

def get_domain_from_url(url):
    """Extracts the base domain (e.g., 'example.com') from a URL."""
    try:
        parsed_url = urlparse(url)
        # We use .netloc which gives 'www.example.com', then split
        domain_parts = parsed_url.netloc.split('.')
        # Take the last two parts for standard domains like .com, .org, etc.
        # This is a simplification and might need adjustment for TLDs like .co.uk
        if len(domain_parts) > 1:
            return f"{domain_parts[-2]}.{domain_parts[-1]}"
        return parsed_url.netloc
    except Exception:
        return None

def get_rdap_server(tld):
    """
    Returns the RDAP server URL for a given TLD by querying IANA's RDAP bootstrap service.
    """
    try:
        response = requests.get("https://data.iana.org/rdap/dns.json", headers=HEADERS, timeout=10)
        response.raise_for_status()
        rdap_data = response.json()
        for entry in rdap_data['services']:
            tlds = entry[0]
            rdap_urls = entry[1]
            if tld in tlds:
                return rdap_urls[0]  # Return the first RDAP URL for the TLD
        return None
    except requests.RequestException:
        return None

def is_newly_registered(domain, days=30):
    """
    Checks if a domain was registered within the last 'days' using RDAP.
    Returns True if new, False if not, 'Error' if check fails.
    """
    if not domain:
        return 'N/A'
    try:
        # Extract TLD from domain
        tld = domain.split('.')[-1]
        rdap_server = get_rdap_server(tld)
        if not rdap_server:
            return 'Error'  # No RDAP server found for this TLD

        # Construct RDAP query URL
        rdap_url = f"{rdap_server.rstrip('/')}/domain/{domain}"
        response = requests.get(rdap_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        rdap_data = response.json()

        # Extract creation date from RDAP events
        creation_date = None
        for event in rdap_data.get('events', []):
            if event.get('eventAction') == 'registration':
                creation_date = event.get('eventDate')
                break

        if not creation_date:
            return False  # Info not available, assume not new

        # Parse the creation date (ISO 8601 format, e.g., '2023-10-01T12:00:00Z')
        try:
            creation_datetime = datetime.strptime(creation_date[:19], '%Y-%m-%dT%H:%M:%S')
            return datetime.now() - creation_datetime < timedelta(days=days)
        except ValueError:
            return False  # Invalid date format, assume not new

    except requests.RequestException:
        return 'Error'  # Network or server error
    except Exception:
        return 'Error'  # General error (e.g., JSON parsing or unexpected response)

def check_monetization(url):
    """
    Checks for Google AdSense or Stripe code on a website.
    Returns the name of the tool found, or 'None'.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        html = response.text
        
        found_tools = []
        if re.search(r'adsbygoogle|pagead2\.googlesyndication\.com|ca-pub-', html, re.IGNORECASE):
            found_tools.append("Google AdSense")
            
        if re.search(r'js\.stripe\.com|checkout\.stripe\.com', html, re.IGNORECASE):
            found_tools.append("Stripe")
            
        return ", ".join(found_tools) if found_tools else 'None'
    except requests.RequestException:
        return 'Fetch Error'

# --- UPDATED FETCH FUNCTION ---

def fetch_search_results(query, tbs="qdr:d1", num_results=100):
    """
    Fetches Google search results and scrapes title, description, domain info, 
    and monetization for each URL.
    """
    results = []
    domain_rdap_cache = {}  # Cache RDAP results to avoid redundant checks

    print(f"Fetching up to {num_results} results for query: '{query}'...")

    try:
        urls_to_process = list(search(query, tbs=tbs, num=num_results, stop=num_results, pause=2.0))
        total_urls = len(urls_to_process)
        print(f"Found {total_urls} URLs to analyze.")

        for i, url in enumerate(urls_to_process):
            print(f"\n[{i+1}/{total_urls}] Processing: {url}")
            
            # --- Initialize default values ---
            title = "Processing Error"
            description = "Processing Error"
            domain = "N/A"
            is_new = "N/A"
            monetization = "N/A"
            
            try:
                # 1. Scrape Title and Description
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else "No Title Found"

                description_tag = soup.find('meta', attrs={'name': 'description'})
                description = description_tag['content'].strip() if description_tag and description_tag.get('content') else "No Description Found"
                print(f"  -> Title: {title[:70]}...")

                # 2. Domain and RDAP Check (with Caching)
                domain = get_domain_from_url(url)
                if domain and domain not in domain_rdap_cache:
                    print(f"  -> New Domain Found: {domain}. Checking registration date...")
                    is_new = is_newly_registered(domain, days=30)
                    domain_rdap_cache[domain] = is_new  # Cache the result
                    print(f"  -> Is New (30d): {is_new}")
                elif domain:
                    is_new = domain_rdap_cache[domain]  # Use cached result
                    print(f"  -> Domain: {domain} (already checked)")

                # 3. Monetization Check
                monetization = check_monetization(url)
                print(f"  -> Monetization: {monetization}")

            except requests.exceptions.RequestException as e:
                title = "Error - Could not fetch"
                description = str(e)
                print(f"  -> Error fetching URL: {e}")
            except Exception as e:
                title = "Error - Processing failed"
                description = str(e)
                print(f"  -> An unexpected error occurred: {e}")
            
            # Append all collected data
            results.append({
                "URL": url, 
                "Title": title, 
                "Description": description,
                "Domain": domain,
                "Is_New_Domain(30d)": is_new,
                "Monetization": monetization
            })
            time.sleep(0.5)

    except Exception as e:
        print(f"A critical error occurred during the Google search phase: {e}")
        print("This might be due to a temporary block from Google. Try again later.")

    return results

def save_to_csv(results, folder_name="results", filename="results.csv"):
    """
    Saves results to a CSV file. If the file already exists, it appends the 
    new results and removes duplicates based on the URL.
    """
    if not results:
        print("No new results to save.")
        return

    os.makedirs(folder_name, exist_ok=True)
    full_path = os.path.join(folder_name, filename)
    new_df = pd.DataFrame(results)

    if os.path.exists(full_path):
        print(f"\nFile '{full_path}' exists. Appending new data and de-duplicating...")
        try:
            existing_df = pd.read_csv(full_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            # keep='last' ensures that if we re-scrape a URL, its data gets updated
            final_df = combined_df.drop_duplicates(subset=['URL'], keep='last')
            rows_added = len(final_df) - len(existing_df)
            print(f"Appended {rows_added} new unique results.")
        except pd.errors.EmptyDataError:
            print("Existing file is empty. Saving new results.")
            final_df = new_df
    else:
        print(f"\nCreating new file: '{full_path}'")
        final_df = new_df

    final_df.to_csv(full_path, index=False, encoding='utf-8-sig')
    print(f"Successfully saved. Total unique results in file: {len(final_df)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python domain_checker.py \"<query>\" <timeframe>")
        print("\n<timeframe> can be: 'qdr:h' (hour), 'qdr:d' (day), 'qdr:w' (week), 'qdr:m' (month)")
        sys.exit(1)
        
    query = sys.argv[1]
    timeframe = sys.argv[2]
    
    # --- Main Execution ---
    scraped_results = fetch_search_results(query, tbs=timeframe, num_results=100)

    # Generate a dynamic filename with the current date
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{query}_adsensenew_{date_str}.csv"

    save_to_csv(scraped_results, folder_name="results", filename=filename)
    
    print("\nScript finished.")

import csv
import sys
from googlesearch import search
import pandas as pd

def fetch_search_results(query, num_results=100):
    results = []
    for url in search(query, num_results=num_results, stop=num_results, pause=2):
        # Use BeautifulSoup to fetch the title and description
        # The title is typically the text displayed in the search result.
        title = url.split('/')[2].replace("-", " ").title()
        description = "Description for {}".format(title)
        results.append({"URL": url, "Title": title, "Description": description})
    return results

def save_to_csv(results, filename="google_search_results.csv"):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    query = sys.argv[1]
    results = fetch_search_results(query, num_results=100)
    save_to_csv(results)
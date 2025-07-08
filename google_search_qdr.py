# https://github.com/MarioVilas/googlesearch/issues/122
import csv
import sys
from googlesearch import search
import pandas as pd

def fetch_search_results(query, tbs="qdr:d1",num_results=100):
    results = []
    # Use the num_results to control the number of pages fetched
    for i, url in enumerate(search(query, tbs=tbs,num=num_results)):
        if i >= num_results:
            break
        # Use the URL for the title and description (mocked here)
        title = url.split('/')[2].replace("-", " ").title()
        description = "Description for {}".format(title)
        results.append({"URL": url, "Title": title, "Description": description})
    return results

def save_to_csv(results, filename="google_search_results.csv"):
    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    query = sys.argv[1]
    # specify tbs parameter in search function, like search('"Breaking Code" WordPress blog', tbs="qdr:y1", stop=20), where y[number] / m[number] / d[number] is same as described in dateRestrict parameter here.

# :param str tbs: Time limits (i.e "qdr:h" => last hour,
  # "qdr:y1"
        # "qdr:d" => last 24 hours, "qdr:m" => last month).
    results = fetch_search_results(query, tbs="qdr:h24",num_results=100)
    save_to_csv(results)

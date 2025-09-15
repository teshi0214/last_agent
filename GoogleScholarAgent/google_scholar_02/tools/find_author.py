"""Tool to search Google Scholar for author profiles by name"""

import os
import requests

SERPAPI_API_KEY = "64ba52253fc90fe8ff1cea888a40f6334cc9547588ef51ad1f7cf140c79f4262"

def find_author_tool(name: str) -> dict:
    """Performs a search on Google scholar to search for authors

    args:
    author name

    returns:
    name, link to profile, author_id,
    """

    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "q": f"author:{name}",
        "api_key": SERPAPI_API_KEY,
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()

        found_authors = []
        if "profiles" in results and "authors" in results["profiles"]:
            for author_data in results["profiles"]["authors"]:
                author_profile = {
                    "name": author_data.get("name", "N/A"),
                    "link": author_data.get("link", "N/A"),
                    "author_id": author_data.get("author_id", "N/A"),
                }
                found_authors.append(author_profile)
        else:
            print("""DEBUG: 'profiles' or 'authors' key NOT found
                in SerpApi response for author search.""")

        return {"Authors": found_authors}

    except requests.exceptions.RequestException as e:
        print(f"A request error occurred: {e}")
        return {"error": f"Request error: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": f"Unexpected error: {e}"}

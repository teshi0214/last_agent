"""Tool to search Google News for articles on a given subject"""

import os
import requests

SERPAPI_API_KEY = "64ba52253fc90fe8ff1cea888a40f6334cc9547588ef51ad1f7cf140c79f4262"

def find_news_tool(query: str) -> dict:

    """Performs a search on Google News using SerpApi, limiting results to 5 articles
    and returning only specific details (link, title, snippet).

    Args:
        query: The search query string.

    Returns:
        A dictionary containing a list of up to 5 simplified news article results.
        Each article dictionary will have 'link', 'title', and 'author'.
        Returns an empty dictionary if the request fails or no results are found.
    """

    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_news", 
        "q":query, 
        "api_key": SERPAPI_API_KEY,
        "num": 5,
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        search_results = response.json()

        processed_articles = []
        if "news_results" in search_results:
            for result in search_results["news_results"]:
                article_info = {
                    "title": result.get("title", "N/A"),
                    "link": result.get("link", "N/A"),
                    "author": result.get("author", "N/A")
                }
                processed_articles.append(article_info)

        return {"articles": processed_articles}

    except requests.exceptions.RequestException as e:
        print(f"A request error occurred: {e}")
        return {"error": f"Request error: {e}"}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": f"Unexpected error: {e}"}

"""Tool to search Google Scholar for papers on a given topic"""

import requests

def find_papers_tool(query: str) -> dict:
    """Performs a search on Google Scholar using SerpApi, limiting results to 5 articles."""

    SERPAPI_API_KEY = "64ba52253fc90fe8ff1cea888a40f6334cc9547588ef51ad1f7cf140c79f4262"

    if not SERPAPI_API_KEY:
        return {"error": "SERPAPI_API_KEY not set in code."}

    base_url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_scholar",
        "q": query,
        "api_key": SERPAPI_API_KEY,
        "as_ylo": "2000",
        "num": 5,
    }

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        search_results = response.json()

        processed_articles = []
        if "organic_results" in search_results:
            for result in search_results["organic_results"]:
                author_names, author_ids = [], []
                pub = result.get("publication_info", {})
                if isinstance(pub, dict):
                    if "authors" in pub:
                        for author in pub["authors"]:
                            author_names.append(author.get("name", "N/A"))
                            author_ids.append(author.get("author_id", "N/A"))
                    elif "summary" in pub:
                        author_names.append(pub.get("summary", "N/A"))

                processed_articles.append({
                    "title": result.get("title", "N/A"),
                    "link": result.get("link", "N/A"),
                    "snippet": result.get("snippet", "N/A"),
                    "author_names": author_names,
                    "author_ids": author_ids,
                })

        return {"articles": processed_articles}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {e}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}
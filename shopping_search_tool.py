"""
title: Shopping Search Tool
author: Local LLM
description: Search Amazon, eBay, Temu, and AliExpress for products using SearXNG
version: 2.0.0
"""

import requests
import json
import urllib.parse
from typing import Optional


class Tools:
    def __init__(self):
        self.searxng_url = "http://localhost:8080"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
        }

    def _searxng_search(self, query: str, site: str = "", max_results: int = 5) -> list:
        """Internal: search via local SearXNG instance"""
        try:
            search_query = f"site:{site} {query}" if site else query
            params = {
                "q": search_query,
                "format": "json",
                "categories": "general",
                "language": "en-US",
            }
            resp = requests.get(
                f"{self.searxng_url}/search",
                params=params,
                headers=self.headers,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])[:max_results]
            return []
        except Exception as e:
            return []

    def search_amazon(self, query: str, max_results: int = 5) -> str:
        """
        Search Amazon for products matching the query.
        :param query: The product search query (e.g. 'wireless headphones', 'gaming mouse')
        :param max_results: Maximum number of results to return (default 5)
        :return: JSON string with product listings from Amazon
        """
        try:
            results = self._searxng_search(query, "amazon.com", max_results)
            if results:
                formatted = []
                for r in results:
                    formatted.append({
                        "store": "Amazon",
                        "title": r.get("title", "N/A"),
                        "url": r.get("url", "N/A"),
                        "description": r.get("content", "")[:200],
                    })
                return json.dumps({"store": "Amazon", "query": query, "results": formatted}, indent=2)
            # Fallback: direct Amazon search link
            encoded = urllib.parse.quote(query)
            return json.dumps({
                "store": "Amazon",
                "query": query,
                "search_url": f"https://www.amazon.com/s?k={encoded}",
                "note": "Click the search URL to browse Amazon results directly."
            })
        except Exception as e:
            return json.dumps({"store": "Amazon", "error": str(e)})

    def search_ebay(self, query: str, max_results: int = 5) -> str:
        """
        Search eBay for products matching the query.
        :param query: The product search query (e.g. 'vintage camera', 'iphone 15')
        :param max_results: Maximum number of results to return (default 5)
        :return: JSON string with product listings from eBay
        """
        try:
            results = self._searxng_search(query, "ebay.com", max_results)
            if results:
                formatted = []
                for r in results:
                    formatted.append({
                        "store": "eBay",
                        "title": r.get("title", "N/A"),
                        "url": r.get("url", "N/A"),
                        "description": r.get("content", "")[:200],
                    })
                return json.dumps({"store": "eBay", "query": query, "results": formatted}, indent=2)
            encoded = urllib.parse.quote(query)
            return json.dumps({
                "store": "eBay",
                "query": query,
                "search_url": f"https://www.ebay.com/sch/i.html?_nkw={encoded}",
                "note": "Click the search URL to browse eBay results directly."
            })
        except Exception as e:
            return json.dumps({"store": "eBay", "error": str(e)})

    def search_aliexpress(self, query: str, max_results: int = 5) -> str:
        """
        Search AliExpress for products matching the query.
        :param query: The product search query (e.g. 'led strip lights', 'phone case')
        :param max_results: Maximum number of results to return (default 5)
        :return: JSON string with product listings from AliExpress
        """
        try:
            results = self._searxng_search(query, "aliexpress.com", max_results)
            if results:
                formatted = []
                for r in results:
                    formatted.append({
                        "store": "AliExpress",
                        "title": r.get("title", "N/A"),
                        "url": r.get("url", "N/A"),
                        "description": r.get("content", "")[:200],
                    })
                return json.dumps({"store": "AliExpress", "query": query, "results": formatted}, indent=2)
            encoded = urllib.parse.quote(query)
            return json.dumps({
                "store": "AliExpress",
                "query": query,
                "search_url": f"https://www.aliexpress.com/wholesale?SearchText={encoded}",
                "note": "Click the search URL to browse AliExpress results directly."
            })
        except Exception as e:
            return json.dumps({"store": "AliExpress", "error": str(e)})

    def search_temu(self, query: str, max_results: int = 5) -> str:
        """
        Search Temu for products matching the query.
        :param query: The product search query (e.g. 'kitchen gadgets', 'yoga mat')
        :param max_results: Maximum number of results to return (default 5)
        :return: JSON string with product listings from Temu
        """
        try:
            results = self._searxng_search(query, "temu.com", max_results)
            if results:
                formatted = []
                for r in results:
                    formatted.append({
                        "store": "Temu",
                        "title": r.get("title", "N/A"),
                        "url": r.get("url", "N/A"),
                        "description": r.get("content", "")[:200],
                    })
                return json.dumps({"store": "Temu", "query": query, "results": formatted}, indent=2)
            encoded = urllib.parse.quote(query)
            return json.dumps({
                "store": "Temu",
                "query": query,
                "search_url": f"https://www.temu.com/search_result.html?search_key={encoded}",
                "note": "Click the search URL to browse Temu results directly."
            })
        except Exception as e:
            return json.dumps({"store": "Temu", "error": str(e)})

    def search_all_stores(self, query: str, max_results: int = 5) -> str:
        """
        Search Amazon, eBay, Temu, and AliExpress simultaneously for products and compare prices.
        :param query: The product search query (e.g. 'bluetooth speaker', 'running shoes')
        :param max_results: Maximum number of results per store (default 5)
        :return: JSON string with combined product listings from all 4 stores for price comparison
        """
        all_results = {}

        amazon = json.loads(self.search_amazon(query, max_results))
        all_results["Amazon"] = amazon

        ebay = json.loads(self.search_ebay(query, max_results))
        all_results["eBay"] = ebay

        aliexpress = json.loads(self.search_aliexpress(query, max_results))
        all_results["AliExpress"] = aliexpress

        temu = json.loads(self.search_temu(query, max_results))
        all_results["Temu"] = temu

        return json.dumps({
            "query": query,
            "stores_searched": ["Amazon", "eBay", "AliExpress", "Temu"],
            "results": all_results
        }, indent=2)


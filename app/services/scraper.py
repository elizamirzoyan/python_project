"""
Async fetcher for built-in live datasets.

Each dataset entry maps a short ID to a public API URL. The fetch function
uses aiohttp to make the request concurrently (callers can asyncio.gather
multiple IDs), flattens one level of nesting from each record, and returns
a pandas DataFrame ready for analysis.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import aiohttp
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

BUILT_IN_DATASETS: Dict[str, Dict[str, Any]] = {
    "crypto": {
        "name": "Top 100 Cryptocurrencies",
        "description": "Live prices, market cap, volume, and 24h change for the top 100 coins.",
        "url": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1",
        "category": "Finance",
        "estimated_rows": "~100",
    },
    "countries": {
        "name": "World Countries",
        "description": "Every country on Earth: population, area, region, and subregion.",
        "url": "https://restcountries.com/v3.1/all?fields=name,population,area,region,subregion",
        "category": "Geography",
        "estimated_rows": "~250",
    },
    "people": {
        "name": "Sample User Profiles",
        "description": "Fictional user profiles with names, addresses, emails, and company info.",
        "url": "https://jsonplaceholder.typicode.com/users",
        "category": "Demo",
        "estimated_rows": "~10",
    },
    "posts": {
        "name": "Sample Blog Posts",
        "description": "100 fictional blog posts — good for checking text column quality.",
        "url": "https://jsonplaceholder.typicode.com/posts",
        "category": "Demo",
        "estimated_rows": "~100",
    },
    "todos": {
        "name": "Sample Task List",
        "description": "200 to-do items with completion status. Simple and fast.",
        "url": "https://jsonplaceholder.typicode.com/todos",
        "category": "Demo",
        "estimated_rows": "~200",
    },
    "products": {
        "name": "Product Catalog",
        "description": "100 products with prices, ratings, discount %, stock levels, and categories.",
        "url": "https://dummyjson.com/products?limit=100",
        "list_key": "products",
        "category": "E-commerce",
        "estimated_rows": "~100",
    },
    "spacex": {
        "name": "SpaceX Launches",
        "description": "Every SpaceX rocket launch — mission name, date, success/fail status.",
        "url": "https://api.spacexdata.com/v4/launches",
        "category": "Space",
        "estimated_rows": "~200",
    },
    "nutrition": {
        "name": "Fruit Nutrition Facts",
        "description": "Calories, sugar, protein, fat, and carbs for dozens of fruits.",
        "url": "https://www.fruityvice.com/api/fruit/all",
        "category": "Health",
        "estimated_rows": "~50",
    },
    "quotes": {
        "name": "Famous Quotes",
        "description": "100 quotes with author names. Good for practising with text columns.",
        "url": "https://dummyjson.com/quotes?limit=100",
        "list_key": "quotes",
        "category": "Text",
        "estimated_rows": "~100",
    },
}

MAX_RECORDS = 300


def _flatten_record(record: Any) -> Dict[str, Any]:
    """
    Flatten one level of nesting from a dict record.

    Nested dicts are expanded with underscore-joined keys; nested lists are
    converted to truncated string representations so they stay in a single cell.
    Non-dict top-level values are wrapped in {"value": record}.
    """
    if not isinstance(record, dict):
        return {"value": record}

    flat: Dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if not isinstance(sub_value, (dict, list)):
                    flat[f"{key}_{sub_key}"] = sub_value
        elif isinstance(value, list):
            flat[key] = str(value)[:120] if value else None
        else:
            flat[key] = value
    return flat


async def fetch_dataset(dataset_id: str) -> Tuple[pd.DataFrame, str]:
    """
    Fetch a built-in dataset from the web and return it as a DataFrame.

    Uses asyncio-compatible aiohttp so the server event loop is not blocked
    while waiting for the remote API to respond.

    Args:
        dataset_id: One of the keys in BUILT_IN_DATASETS.

    Returns:
        A tuple of (DataFrame, source_url).

    Raises:
        ValueError:   Unknown dataset ID or unexpected response shape.
        RuntimeError: HTTP error from the upstream API.
    """
    if dataset_id not in BUILT_IN_DATASETS:
        raise ValueError(
            f"Unknown dataset '{dataset_id}'. "
            f"Available: {list(BUILT_IN_DATASETS.keys())}"
        )

    meta = BUILT_IN_DATASETS[dataset_id]
    url: str = meta["url"]
    list_key: Optional[str] = meta.get("list_key")

    timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(f"Could not fetch data — HTTP {response.status}")
            data = await response.json(content_type=None)

    if list_key and isinstance(data, dict):
        data = data.get(list_key, [])

    if not isinstance(data, list):
        raise ValueError("Expected a list of records from the API.")

    records = [_flatten_record(item) for item in data[:MAX_RECORDS]]
    return pd.DataFrame(records), url

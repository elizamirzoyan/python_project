import aiohttp
import pandas as pd
from typing import Dict, Any, Tuple, Optional
import logging
import asyncio 

from app.config import settings

logger = logging.getLogger(__name__)

# Each dataset can optionally have a "list_key" if the API wraps results in an object.
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
        "description": "100 products with prices, ratings, discount %, stock levels, and categories. Great for spotting pricing outliers.",
        "url": "https://dummyjson.com/products?limit=100",
        "list_key": "products",
        "category": "E-commerce",
        "estimated_rows": "~100",
    },
    "spacex": {
        "name": "SpaceX Launches",
        "description": "Every SpaceX rocket launch — mission name, date, success/fail status, and details.",
        "url": "https://api.spacexdata.com/v4/launches",
        "category": "Space",
        "estimated_rows": "~200",
    },
    "nutrition": {
        "name": "Fruit Nutrition Facts",
        "description": "Calories, sugar, protein, fat, and carbs for dozens of fruits. Clean, flat data.",
        "url": "https://www.fruityvice.com/api/fruit/all",
        "category": "Health",
        "estimated_rows": "~50",
    },
    "quotes": {
        "name": "Famous Quotes",
        "description": "100 quotes with author names. Good for practicing with text columns.",
        "url": "https://dummyjson.com/quotes?limit=100",
        "list_key": "quotes",
        "category": "Text",
        "estimated_rows": "~100",
    },
}


def _flatten(record: Any) -> Dict[str, Any]:
    """Flatten one level of nesting from a dict."""
    if not isinstance(record, dict):
        return {"value": record}
    out: Dict[str, Any] = {}
    for k, v in record.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                if not isinstance(sub_v, (dict, list)):
                    out[f"{k}_{sub_k}"] = sub_v
        elif isinstance(v, list):
            out[k] = str(v)[:120] if v else None
        else:
            out[k] = v
    return out



async def fetch_dataset(dataset_id: str) -> Tuple[pd.DataFrame, str]:
    """Fetch a built-in dataset and return (DataFrame, source_url)."""
    if dataset_id not in BUILT_IN_DATASETS:
        raise ValueError(
            f"Unknown dataset '{dataset_id}'. Available: {list(BUILT_IN_DATASETS.keys())}"
        )

    meta = BUILT_IN_DATASETS[dataset_id]
    url: str = meta["url"]
    list_key: Optional[str] = meta.get("list_key")

    timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
    
    max_retries = 3
    delay = 2  # Start with a 2-second delay
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for attempt in range(max_retries):
            async with session.get(url) as response:
                if response.status == 429:
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limited (429) for {dataset_id}. Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2  # Double the wait time for the next attempt
                        continue
                    else:
                        raise RuntimeError("Could not fetch data — HTTP 429 (Rate Limit Exceeded)")
                
                if response.status != 200:
                    raise RuntimeError(f"Could not fetch data — HTTP {response.status}")
                
                data = await response.json(content_type=None)
                break # Success, break out of the retry loop

    # Some APIs wrap the list in an object (e.g. {"products": [...]})
    if list_key and isinstance(data, dict):
        data = data.get(list_key, [])

    if not isinstance(data, list):
        raise ValueError("Expected a list of records from the API")

    # Cap at 300 rows so analysis stays snappy
    records = [_flatten(item) for item in data[:300]]
    return pd.DataFrame(records), url
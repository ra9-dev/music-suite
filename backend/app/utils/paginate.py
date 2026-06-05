"""
Generic async pagination helper for Spotify's offset-based endpoints.

Spotify uses offset/limit pagination with a `next` field in the response
that is set to null when the last page has been reached.

Usage:
    async for item in paginate_spotify(client, url, headers, limit=100):
        process(item)
"""

import asyncio
from typing import AsyncGenerator

import httpx


async def paginate_spotify(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    params: dict | None = None,
    limit: int = 50,
) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields every item across all pages of a Spotify endpoint.

    Args:
        client:  An open httpx.AsyncClient — caller owns lifecycle.
        url:     The Spotify API endpoint URL (without query params).
        headers: Auth headers, e.g. {"Authorization": "Bearer <token>"}.
        params:  Extra query params merged with limit/offset on each request.
        limit:   Page size. Max 50 for all current Spotify endpoints.

    Yields:
        Individual items from the `items` array on each page.

    Raises:
        httpx.HTTPStatusError on non-2xx responses (rate limits, auth failures, etc.)
    """
    base_params = params or {}
    offset = 0

    while True:
        response = await client.get(
            url,
            headers=headers,
            params={**base_params, "limit": limit, "offset": offset},
        )

        # Retry once on 429 (rate limit) using the Retry-After header
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            await asyncio.sleep(retry_after)
            response = await client.get(
                url,
                headers=headers,
                params={**base_params, "limit": limit, "offset": offset},
            )

        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        for item in items:
            # Spotify occasionally returns null items (e.g. deleted playlist entries)
            # Callers handle None checks in their own logic
            yield item

        # Stop when Spotify signals there are no more pages
        if not data.get("next"):
            break

        offset += limit

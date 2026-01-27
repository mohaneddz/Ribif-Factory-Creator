"""
Search provider implementations for Perplexity, Tavily, SerpAPI, and DuckDuckGo.

Provides unified interface for finding machine/material suppliers and enrichment data.
Includes optional Gemini enhancement for URL discovery.
"""

import logging
from typing import List, Dict, Any, Optional
import asyncio
import httpx
import re

from .database import settings

logger = logging.getLogger(__name__)

# Try to import Gemini helper (optional)
try:
    from .gemini_provider import generate_text
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ============================================================================
# PERPLEXITY INTEGRATION
# ============================================================================

async def search_perplexity(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using Perplexity API.
    
    Returns list of results with: title, url, snippet
    Perplexity provides AI-curated answers with citations.
    
    Troubleshooting 400 errors:
    - API key may have expired: regenerate at https://www.perplexity.ai/api/
    - Model name may have changed: verify current model at Perplexity docs
    - Account may need activation or upgrade
    """
    if not settings.PERPLEXITY_API_KEY:
        logger.warning("Perplexity API key not configured")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-sonar-large-128k-online",  # Check Perplexity docs if 400 error
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that finds industrial equipment suppliers. Return only factual information with URLs."
                        },
                        {
                            "role": "user",
                            "content": f"Find suppliers for: {query}. Include company names, websites, and contact information."
                        }
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract citations/URLs from Perplexity response
            results = []
            if "citations" in data:
                for citation in data.get("citations", [])[:max_results]:
                    results.append({
                        "title": citation.get("title", ""),
                        "url": citation.get("url", ""),
                        "snippet": citation.get("snippet", ""),
                    })

            # Also parse the content for URLs if citations aren't available
            if not results and "choices" in data:
                content = data["choices"][0].get("message", {}).get("content", "")
                # Simple URL extraction from content
                urls = re.findall(r'https?://[^\s\)]+', content)
                for url in urls[:max_results]:
                    results.append({
                        "title": "",
                        "url": url,
                        "snippet": content[:200] if content else "",
                    })

            logger.info(f"Perplexity found {len(results)} results for: {query}")
            return results
    except Exception as e:
        logger.error(f"Perplexity search error: {e}")
        return []


# ============================================================================
# TAVILY INTEGRATION
# ============================================================================

async def search_tavily(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using Tavily API.
    
    Tavily provides web search with AI-powered relevance ranking.
    Returns list of results with: title, url, snippet
    """
    if not settings.TAVILY_API_KEY:
        logger.warning("Tavily API key not configured")
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for result in data.get("results", [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("content", "")[:500],
                })

            logger.info(f"Tavily found {len(results)} results for: {query}")
            return results
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return []


# ============================================================================
# SERPAPI INTEGRATION
# ============================================================================

async def search_serpapi(query: str, max_results: int = 10, region: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search using SerpAPI (Google Search).
    
    Returns list of results with: title, url, snippet
    """
    if not settings.SERPAPI_KEY:
        logger.warning("SerpAPI key not configured")
        return []

    try:
        params = {
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "q": query,
            "num": max_results,
        }

        if region:
            params["gl"] = region.lower()  # Country code (e.g., "us", "eu", "de")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for result in data.get("organic_results", [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                })

            logger.info(f"SerpAPI found {len(results)} results for: {query}")
            return results
    except Exception as e:
        logger.error(f"SerpAPI search error: {e}")
        return []


# ============================================================================
# DUCKDUCKGO INTEGRATION (Free Fallback)
# ============================================================================

async def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search using DuckDuckGo (free, no API key needed).
    
    Returns list of results with: title, url, snippet
    Useful as fallback when paid APIs are unavailable or rate-limited.
    """
    try:
        from ddgs import DDGS
    except ImportError:
        logger.warning("ddgs not installed")
        return []
    
    try:
        with DDGS() as ddgs:
            results = []
            for res in list(ddgs.text(query, max_results=max_results)):
                results.append({
                    "title": res.get('title', ''),
                    "url": res.get('href', ''),
                    "snippet": res.get('body', '')[:500],
                })
            
            logger.info(f"DuckDuckGo found {len(results)} results for: {query}")
            return results
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return []


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

async def search_all_providers(
    query: str,
    max_results: int = 10,
    region: Optional[str] = None,
    providers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Search across all configured providers with intelligent fallback chain.
    
    Priority order:
    1. Perplexity (AI-curated, best understanding)
    2. Tavily (AI-ranked web search)
    3. SerpAPI (Google quality)
    4. DuckDuckGo (free fallback, always available)
    5. Gemini (optional: generate supplier URLs as last resort)
    
    Deduplicates results by URL and returns merged list.
    
    Args:
        query: Search query
        max_results: Max results to return
        region: Target region (US, EU, CN, etc.)
        providers: List of providers to use. If None, uses all configured.
    
    Returns:
        Combined and deduplicated list of search results.
    """
    all_results = []
    seen_urls = set()

    # Determine which providers to use
    if providers is None:
        providers = ["perplexity", "tavily", "serpapi", "duckduckgo"]
    
    # Build tasks for parallel execution
    tasks = []
    task_providers = []
    
    if "perplexity" in providers and settings.PERPLEXITY_API_KEY:
        tasks.append(search_perplexity(query, max_results))
        task_providers.append("perplexity")
    
    if "tavily" in providers and settings.TAVILY_API_KEY:
        tasks.append(search_tavily(query, max_results))
        task_providers.append("tavily")
    
    if "serpapi" in providers and settings.SERPAPI_KEY:
        tasks.append(search_serpapi(query, max_results, region))
        task_providers.append("serpapi")
    
    if "duckduckgo" in providers:
        tasks.append(search_duckduckgo(query, max_results))
        task_providers.append("duckduckgo")
    
    if not tasks:
        logger.warning("No search providers configured or available")
        return []
    
    # Execute all searches concurrently
    try:
        provider_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider_name, results in zip(task_providers, provider_results):
            if isinstance(results, Exception):
                logger.error(f"{provider_name} search error: {results}")
                continue
            
            for result in results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    result["source"] = provider_name  # Tag source
                    all_results.append(result)
                    
                    if len(all_results) >= max_results:
                        break
            
            if len(all_results) >= max_results:
                break
    
    except Exception as e:
        logger.error(f"Error running concurrent searches: {e}")
    
    # Optionally ask Gemini for additional supplier URLs (LLM-assisted discovery)
    if HAS_GEMINI and settings.GEMINI_API_KEY and len(all_results) < max_results // 2:
        try:
            prompt = f"Provide up to {max_results} supplier website URLs (full http/https links) for: {query}. Respond with plain URLs only, separated by newlines."
            gemini_text = await generate_text(prompt, max_output_tokens=400)
            
            urls = re.findall(r'https?://[^\s\)]+', gemini_text)
            for url in urls:
                if url not in seen_urls and len(all_results) < max_results:
                    seen_urls.add(url)
                    all_results.append({
                        "title": "",
                        "url": url,
                        "snippet": "(from Gemini)",
                        "source": "gemini"
                    })
        except Exception as e:
            logger.debug(f"Gemini enhancement skipped: {e}")
    
    logger.info(f"Combined search returned {len(all_results)} results from {len(task_providers)} providers")
    return all_results[:max_results]

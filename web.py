import asyncio
import httpx
from lxml import etree
import re

SEED_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

source_map = {
    'https://feeds.bbci.co.uk/news/world/rss.xml': 'BBC',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html': 'CNBC',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml': 'NYT',
    'https://www.aljazeera.com/xml/rss/all.xml': 'Al Jazeera'
}

async def fetch_and_parse_feed(client, url):
    """Helper function to handle a single feed request and parse its XML."""
    try:
        response = await client.get(url, headers={'User-Agent': 'RUA-AI/1.0'}, timeout=5.0)
        if response.status_code != 200:
            return []

        root = etree.fromstring(response.content)
        # Extract source name using source_map
        source_name = source_map.get(url)
        
        feed_items = []
        # Get top 5 items per feed
        items = root.findall(".//item")[:5]
        for item in items:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")

            if description:
                description = re.sub('<[^<]+?>', '', description).strip()

            feed_items.append({
                "source": source_name,
                "title": title,
                "summary": description[:200] + "..." if description else "",
                "link": link
            })
        return feed_items
    except Exception:
        # If one feed fails, return an empty list so others can still succeed
        return []

async def get_world_news():
    """
    Fetches the latest global headlines from major news outlets simultaneously.
    Use this when the user asks 'What's going on in the world?' or for recent events.
    """
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        # 1. Create a list of 'tasks' (one for each URL)
        tasks = [fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
        
        # 2. Fire them all at once and wait for the results
        # results will be a list of lists: [[news from bbc], [news from nyt], ...]
        results_of_lists = await asyncio.gather(*tasks)

        # 3. Flatten the list of lists into a single list of articles
        all_articles = [item for sublist in results_of_lists for item in sublist]

    if not all_articles:
        return "The global news grid is unresponsive, sir. I'm unable to pull headlines."

    # 4. Format the final briefing
    report = ["### GLOBAL NEWS BRIEFING (LIVE)\n"]
    # Limit to top 12 items so the AI doesn't get overwhelmed
    for entry in all_articles[:12]:
        report.append(f"**[{entry['source']}]** {entry['title']}")
        report.append(f"{entry['summary']}")
        report.append(f"Link: {entry['link']}\n")

    return "\n".join(report)

# test = asyncio.run(get_world_news())
# print(test)

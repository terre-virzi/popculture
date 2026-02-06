"""
Pop Culture Scraper - Scrapes Reddit for top pop culture news and opinions,
then uses OpenAI to produce a Gen Z-focused summary.
"""

import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Pop culture subreddits - curated for widely-known, funny, mainstream content
SUBREDDITS = [
  # Tier A: event sources (higher weight)
  {"name":"entertainment","tier":"A","cap":35,"weight":1.25},
  {"name":"movies","tier":"A","cap":25,"weight":1.15},
  {"name":"television","tier":"A","cap":25,"weight":1.15},
  {"name":"popculturechat","tier":"A","cap":35,"weight":1.20},
  {"name":"popheads","tier":"A","cap":25,"weight":1.10},
  {"name":"hiphopheads","tier":"A","cap":20,"weight":1.10},
  {"name":"boxoffice","tier":"A","cap":15,"weight":1.05},
  {"name":"LiveFromNewYork","tier":"A","cap":15,"weight":1.05},
  {"name":"TikTokCringe","tier":"A","cap":20,"weight":1.05},

  # Tier B: reaction validation (lower weight + lower cap)
  {"name":"BlackPeopleTwitter","tier":"B","cap":12,"weight":0.85},
  {"name":"WhitePeopleTwitter","tier":"B","cap":12,"weight":0.85},
  {"name":"memes","tier":"B","cap":12,"weight":0.80},
  {"name":"me_irl","tier":"B","cap":10,"weight":0.75},

  # Tier C: gossip (very capped)
  {"name":"Fauxmoi","tier":"C","cap":10,"weight":0.70},
]

# Reddit requires a descriptive User-Agent
USER_AGENT = "PopCultureScraper/1.0 (Gen Z weekly roundup)"


def scrape_reddit() -> list[dict]:
    """Scrape Reddit for top pop culture posts from the past 2 weeks."""
    all_posts: list[dict] = []
    seen_ids: set[str] = set()
    cutoff_utc = time.time() - (14 * 24 * 60 * 60)  # 2 weeks ago

    for sub in SUBREDDITS:
        sub_name = sub["name"] if isinstance(sub, dict) else sub
        for sort in ("top", "hot", "rising"):
            url = f"https://www.reddit.com/r/{sub_name}/{sort}.json"
            if sort == "top":
                params = {"t": "month", "limit": 100}
            elif sort == "rising":
                params = {"limit": 50}  # Catch emerging viral content
            else:
                params = {"limit": 75}  # hot = currently trending
            try:
                r = requests.get(
                    url,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"  Failed r/{sub_name} ({sort}): {e}")
                continue

            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                pid = post.get("id")
                if not pid or pid in seen_ids:
                    continue
                seen_ids.add(pid)

                title = (post.get("title") or "").strip()
                selftext = (post.get("selftext") or "").strip()[:800]
                if not title:
                    continue

                created = post.get("created_utc") or 0
                if created < cutoff_utc:
                    continue  # Skip posts older than 2 weeks

                all_posts.append({
                    "id": pid,
                    "title": title,
                    "selftext": selftext,
                    "subreddit": sub_name,
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc"),
                })

    # Sort by engagement (score + comments) - prioritize viral/funny
    all_posts.sort(key=lambda p: p["score"] + p["num_comments"] * 2, reverse=True)
    return all_posts[:250]


def build_content_summary(posts: list[dict]) -> str:
    """Build text summary for OpenAI."""
    lines = []
    for i, p in enumerate(posts[:200], 1):
        body = f"\n{p['selftext']}" if p["selftext"] else ""
        lines.append(
            f"[{i}] r/{p['subreddit']} | {p['score']} upvotes, {p['num_comments']} comments\n"
            f"{p['title']}{body}"
        )
    return "\n\n".join(lines) if lines else "No posts found."


def get_openai_summary(content: str) -> str:
    """Use OpenAI to produce a Gen Z-focused pop culture summary."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not set in .env")

    prompt = """You are a pop culture expert who creates weekly roundups for Gen Z college students. This content will be used for comedy/jokes, so references MUST be widely recognizable.

CRITICAL FILTERING RULES—only include items that pass ALL of these:
1. **Household-name celebrities only**: Taylor Swift, Beyoncé, Trump, Kanye, Drake, Rihanna, Ariana Grande, Billie Eilish, The Rock, etc. If you said the name in a college classroom, 90%+ of students would know who you mean. EXCLUDE: niche influencers, lesser-known YouTubers, indie artists, reality TV side characters, subreddit-specific drama.
2. **Widely circulating events**: Must be trending across multiple platforms (TikTok, Instagram, X, news headlines), not just one small community. The event should have broken out of its bubble—if it's only discussed in one subreddit, skip it.
3. **Joke-understandability test**: Would the majority of a Gen Z audience (18–25) immediately get the reference if someone made a joke about it? If you'd have to explain who the person is or what happened, EXCLUDE IT.
4. **EXCLUDE entirely—never joke about these**: Celebrity deaths, serious tragedies, illnesses, or losses. We don't make fun of people dying or suffering.
5. **Liberal-aligned comedy**: Do NOT include items that roast celebrities for taking progressive/liberal positions (e.g., condemning ICE, supporting immigrants, speaking out for marginalized groups). We're not punching down. If the joke would make someone look bad for doing the right thing, skip it. It's fine to joke about celebrities' drama or antics—but not about them standing up for human rights. It IS fine—and encouraged—to roast Trump, politicians, power institutions, corporations, and the rich/powerful. Punch up, not down.

CONSOLIDATION: If many posts are about the same event (e.g., the Grammys, a major awards show, a single viral moment), COMBINE them into ONE item. Don't list "Billie at the Grammys," "Bad Bunny at the Grammys," "Nicki at the Grammys" separately—roll them into a single "Grammys 2025" (or whatever year) entry that covers the best moments, drama, and memes from that event. Same for any big shared moment: one consolidated entry per event, not one per celebrity.

Your job:
1. List ONLY events that pass the filters above.
2. CONSOLIDATE: Group related posts about the same event into single entries. One event = one item.
3. For each, summarize what happened and the public reaction.
4. When in doubt, EXCLUDE. It's better to have fewer items than to include references that would confuse the audience.

Format each item as:
- **Headline/topic**
- **What actually went down** (brief context)
- **Public reaction** (the jokes, roasts, memes—the vibe)
- **Why it lands** (why most people would get the joke)

Skip anything obscure, niche, or that requires explanation. Sound like a funny friend summarizing the week."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Here are the Reddit posts from the past 2 weeks:\n\n{content}"},
        ],
        max_tokens=2500,
    )
    return response.choices[0].message.content


def main():
    print("Pop Culture Reddit Scraper")
    print("=" * 50)

    if not os.getenv("OPENAI_API_KEY"):
        print("Missing OPENAI_API_KEY in .env")
        return

    print("Scraping Reddit...")
    posts = scrape_reddit()
    print(f"Collected {len(posts)} posts.")

    if not posts:
        print("No posts found.")
        return

    print("\n" + "=" * 50)
    print("REDDIT POSTS (raw)")
    print("=" * 50)
    for i, p in enumerate(posts[:200], 1):
        body = f"\n  {p['selftext'][:300]}..." if len(p.get("selftext", "") or "") > 300 else (f"\n  {p['selftext']}" if p.get("selftext") else "")
        print(f"\n[{i}] r/{p['subreddit']} | {p['score']} upvotes, {p['num_comments']} comments")
        print(f"  {p['title']}{body}")
    print("\n" + "=" * 50)

    print("Sending to OpenAI for Gen Z-focused summary...")
    content = build_content_summary(posts)
    summary = get_openai_summary(content)

    print("\n" + "=" * 50)
    print("GEN Z POP CULTURE ROUNDUP (Past 2 Weeks)")
    print("=" * 50)
    print(summary)

    out_path = Path("pop_culture_roundup.txt")
    out_path.write_text(summary, encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

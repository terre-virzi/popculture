# Pop Culture Scraper

Scrapes Reddit for top pop culture news and opinions from the past week, then uses OpenAI to produce a Gen Z-focused summary. No login required.

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env`** (copy from `.env.example`):
   ```
   OPENAI_API_KEY=sk-your-openai-api-key
   ```

   Get an API key at [platform.openai.com](https://platform.openai.com).

## Run

```bash
python pop_culture_scraper.py
```

Output is printed and saved to `pop_culture_roundup.txt`.

## What it does

1. **Scrapes Reddit** subreddits (r/popculturechat, r/entertainment, r/Fauxmoi, r/television, etc.) for top and hot posts from the past week
2. **Sends** post titles and content to OpenAI
3. **Produces** a summary that explains each event, public opinion, and filters for things Gen Z students would know, find funny, and joke about

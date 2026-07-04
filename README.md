# AI Company Research Assistant

A chat-style app: type a company name or website URL, and get back a
full research report (contact info, products, AI-generated pain points,
competitors) plus a downloadable PDF — with optional auto-posting to Discord.

## How it's built (plain-English map)
- **`serper_client.py`** – talks to Serper.dev to find a company's official
  website (if only a name was given), do general web research, and look
  up competitor websites.
- **`crawler.py`** – visits the company's site, specifically looking for
  Home/About/Products/Services/Pricing/Contact pages. Skips login pages
  and duplicates. Pulls out a phone number and address with pattern matching.
- **`ai_engine.py`** – sends the crawled text + search results to an AI
  model via OpenRouter (you can pick any model OpenRouter supports) and
  gets back a structured summary, pain points, and competitor names.
- **`report_generator.py`** – turns that structured data into a clean PDF.
- **`discord_bot.py`** – optionally sends the finished report straight to
  a Discord channel using a bot token.
- **`app.py`** – the chat-style Streamlit interface tying it all together.

## Required environment variables / API keys
| Variable | Where to get it | Required? |
|---|---|---|
| `SERPER_API_KEY` | https://serper.dev (free tier available) | Yes |
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys | Yes |

Discord Bot Token, Discord Channel ID, Applicant Name, and Applicant Email
are entered directly in the app's sidebar (Settings → Discord Integration),
not as environment variables, since the evaluator provides these live.

## Setup
```bash
pip install -r requirements.txt
export SERPER_API_KEY="your_key_here"
export OPENROUTER_API_KEY="your_key_here"
streamlit run app.py
```

## Using the app
1. Type a company name (e.g. `Stripe`) or a URL (e.g. `https://stripe.com`)
   into the chat box.
2. Wait for the pipeline to run (site discovery → crawl → search → AI
   analysis → competitor lookup). Progress spinners show each stage.
3. The report appears in the chat, with a PDF download button underneath.
4. Ask follow-up questions in the same chat box - it'll answer using the
   research it already gathered.
5. Click "🔄 New Company Search" in the sidebar to start over with a
   different company.

### Optional: Discord integration
1. In the sidebar, open "Discord Integration."
2. Fill in Applicant Name, Applicant Email, Discord Bot Token, Discord
   Channel ID.
3. Click "Save Configuration."
4. From then on, every generated report is automatically posted to that
   Discord channel with the PDF attached.

## Deployment
Streamlit Community Cloud is the fastest option for this stack:
1. Push this folder to a public GitHub repo.
2. Go to https://share.streamlit.io → New app → select the repo, main
   file `app.py`.
3. Under app settings → Secrets, add:
   ```
   SERPER_API_KEY = "your_key_here"
   OPENROUTER_API_KEY = "your_key_here"
   ```
4. Deploy — you get a public URL in about 2 minutes.

## Known limitations
- Free OpenRouter models can be rate-limited or occasionally slow; the
  app retries automatically with a short wait if this happens.
- Phone/address extraction uses simple pattern matching on page text, so
  results may occasionally be imperfect for unusually formatted sites.
- Competitor websites are found via a best-effort search match; if none
  is found, the report shows "Not found" for that competitor.

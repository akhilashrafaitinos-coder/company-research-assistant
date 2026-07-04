"""
app.py
------
Run with: streamlit run app.py

Plain-English flow:
  1. User types a company name or website URL into the chat box.
  2. If it's just a name, Serper.dev finds the official website.
  3. crawler.py visits Home/About/Products/Services/Contact/Pricing pages.
  4. Serper.dev also does a general web search for extra context.
  5. ai_engine.py (via OpenRouter) turns all of that into a structured
     summary: description, products, phone, address, pain points, competitors.
  6. Competitor websites are looked up via Serper too.
  7. A PDF report is generated automatically and offered as a download.
  8. If Discord is configured in Settings, the report is auto-posted there.
  9. Further messages in the chat are treated as follow-up questions
     about the most recently researched company.
"""

import streamlit as st
import time
import os

from serper_client import find_official_website, general_company_search, find_competitor_website
from crawler import crawl_company_site
from ai_engine import analyze_company, chat_about_company, DEFAULT_MODEL
from report_generator import generate_pdf_report
from discord_bot import send_report_to_discord

st.set_page_config(page_title="AI Company Research Assistant", layout="wide", page_icon="🔍")

# ---------------------------------------------------------
# Session state setup
# ---------------------------------------------------------
defaults = {
    "chat_log": [],           # list of {"role": "user"/"assistant", "content": str, "pdf_path": optional}
    "company_data": None,     # most recently researched company's structured data
    "last_run_time": 0,
    "openrouter_model": DEFAULT_MODEL,
    "discord_bot_token": "",
    "discord_channel_id": "",
    "applicant_name": "",
    "applicant_email": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------------
# Sidebar: Settings (model choice + Discord + applicant info)
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    with st.expander("AI Model", expanded=True):
        st.session_state.openrouter_model = st.text_input(
            "OpenRouter model ID",
            value=st.session_state.openrouter_model,
            help="Any model ID supported by OpenRouter, e.g. openai/gpt-4o-mini, "
                 "anthropic/claude-3.5-haiku, meta-llama/llama-3.1-8b-instruct:free. "
                 "See openrouter.ai/models for the full list.",
        )

    with st.expander("Discord Integration (optional)"):
        st.caption("If filled in, each report is automatically sent to this channel.")
        st.session_state.applicant_name = st.text_input("Applicant Name", value=st.session_state.applicant_name)
        st.session_state.applicant_email = st.text_input("Applicant Email", value=st.session_state.applicant_email)
        discord_token_input = st.text_input("Discord Bot Token", value=st.session_state.discord_bot_token, type="password")
        discord_channel_input = st.text_input("Discord Channel ID", value=st.session_state.discord_channel_id)
        if st.button("Save Configuration"):
            st.session_state.discord_bot_token = discord_token_input
            st.session_state.discord_channel_id = discord_channel_input
            st.success("Saved.")

    st.divider()
    if st.button("🔄 New Company Search"):
        st.session_state.company_data = None
        st.session_state.chat_log = []
        st.rerun()


# ---------------------------------------------------------
# Main chat UI
# ---------------------------------------------------------
st.title("🔍 AI Company Research Assistant")
st.caption("Type a company name or website URL to get started.")

for msg in st.session_state.chat_log:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("pdf_path") and os.path.exists(msg["pdf_path"]):
            with open(msg["pdf_path"], "rb") as f:
                st.download_button(
                    "⬇️ Download PDF Report",
                    data=f,
                    file_name=os.path.basename(msg["pdf_path"]),
                    mime="application/pdf",
                    key=f"dl_{msg['pdf_path']}_{id(msg)}",
                )


def render_company_markdown(data: dict) -> str:
    lines = [f"### {data.get('company_name', 'Unknown Company')}"]
    lines.append(f"**Website:** {data.get('website', 'N/A')}  ")
    lines.append(f"**Phone:** {data.get('phone', 'N/A')}  ")
    lines.append(f"**Address:** {data.get('address', 'N/A')}  ")
    lines.append(f"\n{data.get('description', '')}\n")

    lines.append("**Products / Services:**")
    for p in data.get("products_services", []):
        lines.append(f"- {p}")

    lines.append("\n**AI-Generated Pain Points:**")
    for p in data.get("pain_points", []):
        lines.append(f"- {p}")

    lines.append("\n**Competitors:**")
    for c in data.get("competitors", []):
        lines.append(f"- {c.get('name', 'Unknown')} — {c.get('website', 'website not found')}")

    return "\n".join(lines)


def run_research_pipeline(user_input: str) -> dict:
    """The full pipeline: find site -> crawl -> search -> AI analyze -> competitor sites."""
    user_input = user_input.strip()

    if user_input.startswith("http"):
        official_url = user_input
    else:
        with st.spinner("Finding official website via Serper.dev..."):
            official_url = find_official_website(user_input)

    if not official_url:
        return {"error": "Could not find an official website for this company."}

    with st.spinner(f"Crawling {official_url} ..."):
        crawl_result = crawl_company_site(official_url)

    with st.spinner("Searching the web for extra context..."):
        search_snippets = general_company_search(user_input)

    with st.spinner(f"Analyzing with AI ({st.session_state.openrouter_model})..."):
        analysis = analyze_company(
            crawled_text=crawl_result["combined_text"],
            search_snippets=search_snippets,
            company_label=user_input,
            known_phone=crawl_result["phone"],
            known_address=crawl_result["address"],
            model=st.session_state.openrouter_model,
        )

    if analysis.get("error"):
        return {"error": analysis["error"]}

    analysis["website"] = official_url
    analysis.setdefault("phone", crawl_result["phone"])
    analysis.setdefault("address", crawl_result["address"])

    with st.spinner("Looking up competitor websites..."):
        for comp in analysis.get("competitors", []):
            comp["website"] = find_competitor_website(comp.get("name", "")) or "Not found"

    return analysis


user_message = st.chat_input("Enter a company name, a website URL, or ask a follow-up question...")

if user_message:
    seconds_since_last = time.time() - st.session_state.last_run_time
    COOLDOWN = 10
    if seconds_since_last < COOLDOWN:
        st.warning(f"Please wait {int(COOLDOWN - seconds_since_last)}s before sending another request (avoids AI rate limits).")
        st.stop()
    st.session_state.last_run_time = time.time()

    st.session_state.chat_log.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)

    with st.chat_message("assistant"):
        if st.session_state.company_data is None:
            # First message, or after "New Company Search" - treat as a research request
            result = run_research_pipeline(user_message)

            if result.get("error"):
                reply = f"⚠️ {result['error']}"
                st.markdown(reply)
                st.session_state.chat_log.append({"role": "assistant", "content": reply})
            else:
                st.session_state.company_data = result
                reply = render_company_markdown(result)
                st.markdown(reply)

                pdf_path = generate_pdf_report(result, output_path=f"report_{int(time.time())}.pdf")
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ Download PDF Report", data=f, file_name=os.path.basename(pdf_path), mime="application/pdf")

                discord_status = ""
                if st.session_state.discord_bot_token and st.session_state.discord_channel_id:
                    with st.spinner("Sending report to Discord..."):
                        outcome = send_report_to_discord(
                            bot_token=st.session_state.discord_bot_token,
                            channel_id=st.session_state.discord_channel_id,
                            applicant_name=st.session_state.applicant_name,
                            applicant_email=st.session_state.applicant_email,
                            company_name=result.get("company_name", ""),
                            company_website=result.get("website", ""),
                            pdf_path=pdf_path,
                        )
                    if outcome["success"]:
                        st.success("Report sent to Discord ✅")
                    else:
                        st.warning(f"Discord send failed: {outcome['error']}")

                st.session_state.chat_log.append({"role": "assistant", "content": reply, "pdf_path": pdf_path})
        else:
            # Follow-up question about the already-researched company
            with st.spinner("Thinking..."):
                answer = chat_about_company(
                    st.session_state.company_data,
                    st.session_state.chat_log,
                    user_message,
                    model=st.session_state.openrouter_model,
                )
            st.markdown(answer)
            st.session_state.chat_log.append({"role": "assistant", "content": answer})

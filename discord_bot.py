"""
discord_bot.py
---------------
Plain-English job of this file:
  After a report is generated, send a message + the PDF file to a
  Discord channel, using a Discord Bot Token and Channel ID.

  This uses Discord's REST API directly (no discord.py library needed),
  since we only need to send one message with one attachment, not run
  a full always-on bot.
"""

import requests


def send_report_to_discord(bot_token: str, channel_id: str, applicant_name: str,
                            applicant_email: str, company_name: str, company_website: str,
                            pdf_path: str) -> dict:
    """
    Sends a formatted message + the PDF report to the given Discord channel.
    Returns {"success": True} or {"success": False, "error": "..."}
    """
    if not bot_token or not channel_id:
        return {"success": False, "error": "Missing Discord bot token or channel ID."}

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}"}

    message_content = (
        f"**New Company Research Report**\n"
        f"**Applicant:** {applicant_name} ({applicant_email})\n"
        f"**Company:** {company_name}\n"
        f"**Website:** {company_website}"
    )

    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                url,
                headers=headers,
                data={"content": message_content},
                files={"file": (pdf_path.split("/")[-1], f, "application/pdf")},
                timeout=30,
            )

        if resp.status_code in (200, 201):
            return {"success": True}
        return {"success": False, "error": f"Discord API returned {resp.status_code}: {resp.text[:200]}"}

    except FileNotFoundError:
        return {"success": False, "error": f"PDF file not found at {pdf_path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

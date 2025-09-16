import os
import requests
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime

# Load environment variables
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")

# ================= HTML Templates =================
HTML_HEADER = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
    <tr>
      <td align="center" style="padding:28px 12px;">
        <table width="600" cellpadding="0" cellspacing="0" role="presentation" style="background:#ffffff;border-radius:12px;box-shadow:0 6px 18px rgba(20,20,30,0.06);overflow:hidden;">
          <tr>
            <td style="padding:28px 36px;">
              <div style="font-size:24px;font-weight:700;color:#0f172a;">🚀 Daily AI & Dev Digest</div>
              <div style="font-size:15px;color:#6b7280;margin-bottom:20px;">{date}</div>
"""

HTML_FOOTER = """
              <div style="margin-top:24px;font-size:13px;color:#9ca3af;border-top:1px solid #eef2f7;padding-top:14px;">
                You are receiving this because you asked your AI agent to send daily updates.
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

ITEM_CARD = """
<div style="margin-bottom:18px;padding:16px;background:#f8fafc;border-radius:10px;border:1px solid #eef2f7;">
  <div style="font-size:20px;font-weight:700;color:#0f172a;margin-bottom:8px;line-height:1.25;">{title}</div>
  <div style="font-size:16px;color:#334155;margin-bottom:12px;line-height:1.45;">{summary}</div>
  <a href="{url}" style="display:inline-block;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px;background:#0f172a;color:#ffffff;">Read more</a>
</div>
"""

# ================= Summarizer =================
def summarize_text(text):
    url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": text[:2000]}  # limit length for safety
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        if isinstance(result, list) and "summary_text" in result[0]:
            return result[0]["summary_text"]
        return text  # fallback
    except Exception as e:
        print("Summarization error:", e)
        return text

# ================= Fetch News =================
def fetch_newsapi():
    url = "https://newsapi.org/v2/everything"
    query = "AI AND (Development OR Developers OR Programming OR Tools OR Frameworks)"
    params = {
        "q": query,
        "language": "en",
        "pageSize": 5,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY
    }
    res = requests.get(url, params=params)
    data = res.json()
    return data.get("articles", [])

def fetch_hn():
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": "AI developer OR AI tools OR programming OR framework",
        "tags": "story",
        "hitsPerPage": 5
    }
    res = requests.get(url, params=params)
    data = res.json()
    return data.get("hits", [])

# ================= Build Digest =================
def build_digest():
    articles = []

    # NewsAPI
    for art in fetch_newsapi():
        title = art.get("title", "Untitled")
        url = art.get("url", "#")
        # Combine title + description + content
        content = f"{art.get('title','')}. {art.get('description','')}. {art.get('content','')}"
        summary = summarize_text(content)
        articles.append({"title": title, "summary": summary, "url": url})

    # Hacker News
    for hn in fetch_hn():
        title = hn.get("title", "Untitled")
        url = hn.get("url") or f"https://news.ycombinator.com/item?id={hn['objectID']}"
        summary = summarize_text(title)
        articles.append({"title": title, "summary": summary, "url": url})

    # Build HTML
    today = datetime.now().strftime("%B %d, %Y")
    content = HTML_HEADER.format(date=today)

    for art in articles:
        content += ITEM_CARD.format(title=art["title"], summary=art["summary"], url=art["url"])

    content += HTML_FOOTER
    return content

# ================= Send Email =================
def send_email(content):
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject=f"🚀 Your Daily AI & Dev Digest - {datetime.now().strftime('%b %d, %Y')}",
        html_content=content
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print("Email sent:", response.status_code)
    except Exception as e:
        print("SendGrid error:", e)

# ================= Main =================
if __name__ == "__main__":
    digest = build_digest()
    send_email(digest)

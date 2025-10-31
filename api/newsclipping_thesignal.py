# api/newsclipping_thesignal.py
import io
import csv
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# === 설정 ===
BASE_URL = "https://signalm.sedaily.com/Main/Content/SubMain"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://signalm.sedaily.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"
}
CUTOFF_TIME = datetime.now() - timedelta(hours=24)
fieldnames = ["title", "link", "summary", "published_at"]

def parse_time_text(time_str):
    return datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")

def get_page_articles(page):
    params = {
        "NClass": "GX11",
        "Page": page,
        "Kind": "Time"
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        return []

    articles = []
    news_list = soup.select("div.contPadding")
    if not news_list:
        return []

    for item in news_list:
        try:
            a_tag = item.select_one("a")
            if not a_tag: continue

            title = a_tag.select_one("strong")
            if title: title = title.get_text(strip=True)

            link = "https://signalm.sedaily.com" + a_tag['href'] if a_tag['href'].startswith('/') else a_tag['href']

            time_tag = item.select_one("span.time")
            if not time_tag: continue
            published_at = parse_time_text(time_tag.get_text())

            summary = item.select_one("span.mmsn_con")
            if summary: summary = summary.get_text(strip=True)

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published_at": published_at.strftime("%Y-%m-%d %H:%M")
            })
        except:
            continue
    return articles

def scrape_recent_articles():
    all_articles = []
    page = 1
    max_pages = 10

    while page <= max_pages:
        articles = get_page_articles(page)
        if not articles:
            break

        recent_articles = []
        for art in articles:
            pub_time = art["published_at"]
            if pub_time:
                pub_dt = datetime.strptime(pub_time, "%Y-%m-%d %H:%M")
                if pub_dt >= CUTOFF_TIME:
                    recent_articles.append(art)
                else:
                    return all_articles + recent_articles
            else:
                recent_articles.append(art)

        all_articles.extend(recent_articles)

        if len(recent_articles) < len(articles):
            break
        page += 1
        time.sleep(0.5)  # 너무 빠른 요청 방지

    return all_articles

# === Vercel 핸들러 (동기 함수, Any 제거) ===
def handler(event, context=None):
    try:
        print("Starting scrape...")
        articles = scrape_recent_articles()
        print(f"Found {len(articles)} articles")

        if not articles:
            articles = [{"title": "No recent articles", "link": "", "summary": "", "published_at": ""}]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(articles)
        csv_content = output.getvalue()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/csv; charset=utf-8",
                "Content-Disposition": "attachment; filename=signal_news_24h.csv",
                "Cache-Control": "no-cache"
            },
            "body": csv_content
        }
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        return {
            "statusCode": 500,
            "body": error_msg
        }
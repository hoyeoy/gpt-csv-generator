from flask import Flask, Response, jsonify
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import io
import time
import re


app = Flask(__name__)

BASE_URL = "https://signalm.sedaily.com/Main/Content/SubMain"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://signalm.sedaily.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"
}
CUTOFF_TIME = datetime.now() - timedelta(hours=24)

fieldnames = ["title", "link", "summary", "published_at"]

# === 기존 함수들 그대로 사용 ===
def parse_time_text(time_str):
    return datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")

def get_page_articles(page):
    params = {"NClass": "GX11", "Page": page, "Kind": "Time"}
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
    except Exception as e:
        print(f"페이지 {page} 요청 실패: {e}")
        return []

    news_list = soup.select("div.contPadding")
    if not news_list:
        return []

    articles = []
    for item in news_list:
        try:
            a_tag = item.select_one("a")
            if not a_tag:
                continue
            title_tag = a_tag.select_one("strong")
            title = title_tag.get_text(strip=True) if title_tag else None
            link = "https://signalm.sedaily.com" + a_tag['href'] if a_tag['href'].startswith('/') else a_tag['href']
            time_tag = item.select_one("span.time")
            if not time_tag:
                continue
            published_at = parse_time_text(time_tag.get_text())
            summary_tag = item.select_one("span.mmsn_con")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""
            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published_at": published_at.strftime("%Y-%m-%d %H:%M")
            })
        except Exception as e:
            print(f"기사 파싱 오류: {e}")
            continue
    return articles


# === Flask 엔드포인트 ===
@app.route("/api/thesignal", methods=["GET"])
def thesignal():
    """24시간 내 뉴스 스크래핑 후 CSV로 반환"""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    all_articles = []
    page = 1
    max_pages = 10

    while page <= max_pages:
        articles = get_page_articles(page)
        if not articles:
            break

        for art in articles:
            pub_dt = datetime.strptime(art["published_at"], "%Y-%m-%d %H:%M")
            if pub_dt >= CUTOFF_TIME:
                writer.writerow(art)
                all_articles.append(art)
            else:
                # 오래된 기사면 종료
                page = max_pages + 1
                break
        page += 1
        time.sleep(0.8)

    """csv_bytes = output.getvalue().encode("cp949")
    output.close()

    # Flask Response로 CSV 파일 다운로드 전송
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=news_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        }
    )"""

    # ✅ CSV 대신 JSON 반환
    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(all_articles),
        "articles": all_articles
    })

"""// 기존: res.setHeader("Content-Type", "text/csv");
// 수정: res.setHeader("Content-Type", "application/json");

// CSV → JSON 변환
const data = await getNewsData();
return res.status(200).json(data);"""
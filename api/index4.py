from flask import Flask, jsonify, Response, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from urllib.parse import urljoin, quote
import io
import csv
from pytz import timezone

app = Flask(__name__)

# ===============================
# 🔧 기본 설정
# ===============================
YESTERDAY = (datetime.now(timezone('Asia/Seoul')) - timedelta(hours=24)).strftime('%Y.%m.%d')
TODAY = datetime.now(timezone('Asia/Seoul')).strftime('%Y.%m.%d')
"""YESTERDAY = (datetime.now() - timedelta(hours=24)).strftime('%Y.%m.%d')
TODAY = datetime.now().strftime('%Y.%m.%d')
"""
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"
}


# ===============================
# 📰 인베스트조선 뉴스 크롤러
# ===============================
def get_todays_investchosun_news():
    titles, bodies, urls = [], [], []
    page = 1
    max_pages = 30

    session = requests.Session()
    base_url = "https://www.investchosun.com/svc/news/list.html"

    while page <= max_pages:
        params = {"catid": "2", "pn": str(page)}

        try:
            resp = session.get(base_url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            article_items = soup.select("ul.list_ul > li")
            if not article_items:
                break

            page_has_today = False

            for li in article_items:
                dt = li.find("dt")
                if not dt:
                    continue

                a_tag = dt.find("a", href=True)
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                relative_url = a_tag["href"]
                full_url = urljoin("https://www.investchosun.com", relative_url)

                dd_summary = li.find("dd", class_="summary")
                body = ""
                if dd_summary:
                    summary_a = dd_summary.find("a")
                    if summary_a:
                        body = " ".join(summary_a.get_text(strip=True).split())
                    else:
                        body = dd_summary.get_text(strip=True)

                dd_date = li.find("dd", class_="date")
                if not dd_date:
                    continue

                date_span = dd_date.find("span")
                if not date_span:
                    continue

                date_text = date_span.get_text(strip=True).strip()

                if date_text not in (YESTERDAY, TODAY):
                    continue

                if full_url in urls:
                    continue

                titles.append(title)
                bodies.append(body)
                urls.append(full_url)
                page_has_today = True

            if not page_has_today and page > 1:
                break

            page += 1
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ {page}페이지 오류: {e}")
            break

    return titles, bodies, urls


# ===============================
# 🧾 CSV 생성 유틸
# ===============================
def create_csv_bytes(titles, bodies, urls):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "Title", "Body", "Hyperlink"])

    for url, title, body in zip(urls, titles, bodies):
        safe_url = quote(url, safe=":/?=&%#")
        hyperlink = f'=HYPERLINK("{safe_url}", "{title.replace("\"", "\"\"")}")'
        writer.writerow([url, title, body, hyperlink])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    output.close()
    return csv_bytes


# ===============================
# 🚀 Flask 엔드포인트
# ===============================
@app.route("/api/investchosun", methods=["GET"])
def crawl_investchosun():
    """
    GET /api/investchosun
    → 어제 날짜 기준 인베스트조선 기사 수집 후 JSON 반환
    """
     
    titles, bodies, urls = get_todays_investchosun_news()

    articles = [
        {"title": t, "body": b, "url": u}
        for t, b, u in zip(titles, bodies, urls)
    ]
 
    return jsonify({
        "date": YESTERDAY,
        "count": len(articles),
        "articles": articles
    })


# ===============================
# 🧪 로컬 실행용
# ===============================
if __name__ == "__main__":
    app.run(debug=True)

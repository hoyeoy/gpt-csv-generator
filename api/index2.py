from flask import Flask, Response, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
import io
import csv
import time

app = Flask(__name__)

# -----------------------------
# 🔹 뉴스 크롤링 함수
# -----------------------------
def get_todays_news():
    today_str = datetime.now().strftime('%Y-%m-%d')
    titles, bodies, urls = [], [], []

    page = 1
    max_pages = 50
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/129.0.0.0 Safari/537.36'
        )
    }

    print(f"🔍 {today_str} 기사 수집 시작...")
    while page <= max_pages:
        url = f"https://www.thebell.co.kr/free/content/article.asp?page={page}&svccode=00"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            article_items = soup.find_all('li', recursive=True)
            if not article_items:
                print(f"⏹️  {page}페이지: 기사 없음 → 종료")
                break

            page_has_today = False
            for li in article_items:
                dl = li.find('dl')
                if not dl:
                    continue

                # 날짜
                date_span = dl.find('span', class_='date')
                if not date_span:
                    continue
                date_text = date_span.get_text(strip=True)
                if not date_text.startswith(today_str):
                    continue

                # 제목
                dt_tag = dl.find('dt')
                if not dt_tag:
                    continue
                title = dt_tag.get_text(strip=True)

                # 요약
                dd_tag = dl.find('dd')
                body = dd_tag.get_text(strip=True).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ') if dd_tag else ''

                # 링크
                a_tag = dl.find('a')
                href = a_tag.get('href') if a_tag else ''
                full_url = urljoin("https://www.thebell.co.kr/free/content/", href) if href else ''

                titles.append(title)
                bodies.append(body)
                urls.append(full_url)
                page_has_today = True

            if not page_has_today and page > 1:
                print(f"⏹️  {page}페이지 이후 오늘 기사 없음 → 종료")
                break

            page += 1
            time.sleep(0.6)
        except Exception as e:
            print(f"❌ {page}페이지 오류: {e}")
            break

    return titles, bodies, urls


# -----------------------------
# 🔹 CSV 변환 함수
# -----------------------------
def create_csv_bytes(titles, bodies, urls):
    """메모리 내에서 CSV 생성 후 bytes 반환"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['URL', 'Title', 'Body', 'Hyperlink'])

    for url, title, body in zip(urls, titles, bodies):
        safe_url = quote(url, safe=':/?=&%#')
        hyperlink = f'=HYPERLINK("{safe_url}", "{title.replace("\"", "\"\"")}")'
        writer.writerow([url, title, body, hyperlink])

    csv_bytes = output.getvalue().encode('utf-8-sig')
    output.close()
    return csv_bytes


# -----------------------------
# 🔹 Flask 엔드포인트
# -----------------------------
@app.route("/api/thebell", methods=["GET"])
def crawl_thebell():
    """
    예시:
    GET /api/thebell?format=csv  → CSV 파일 다운로드
    GET /api/thebell?format=json → JSON 데이터 반환
    """
    # 1️⃣ 크롤링 실행
    titles, bodies, urls = get_todays_news()
    articles = [
        {"title": t, "body": b, "url": u}
        for t, b, u in zip(titles, bodies, urls)
    ]

    # 2️⃣ 요청 포맷 확인
    fmt = request.args.get("format", "csv").lower()

    # 3️⃣ CSV로 응답
    if fmt == "csv":
        csv_bytes = create_csv_bytes(titles, bodies, urls)
        filename = f"thebell_news_{datetime.now().strftime('%Y%m%d')}.csv"
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    # 4️⃣ JSON으로 응답
    elif fmt == "json":
        return jsonify({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "count": len(articles),
            "articles": articles
        })

    else:
        return jsonify({"error": "지원하지 않는 format입니다. csv 또는 json 중 선택하세요."}), 400


# -----------------------------
# 🔹 로컬 테스트용
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)

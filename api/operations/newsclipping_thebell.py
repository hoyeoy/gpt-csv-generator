# api/operations/thebell_news.py
import csv
import io
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote

import requests
from bs4 import BeautifulSoup


def run(params: dict = None):
    """
    params: dict (optional)
        - days_ago: int  (default 1 → 어제)
    반환: pandas.DataFrame
    """
    params = params or {}
    days_ago = params.get("days_ago", 1)
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    titles, bodies, urls = [], [], []
    page = 1
    max_pages = 50
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )
    }

    print(f"[{target_date}] 수집 시작")
    while page <= max_pages:
        url = f"https://www.thebell.co.kr/free/content/article.asp?page={page}&svccode=00"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.find_all("li")
            has_today = False

            for li in items:
                dl = li.find("dl")
                if not dl:
                    continue
                date_span = dl.find("span", class_="date")
                if not date_span or not date_span.get_text(strip=True).startswith(target_date):
                    continue

                # 제목
                dt = dl.find("dt")
                title = dt.get_text(strip=True) if dt else ""
                # 요약
                dd = dl.find("dd")
                body = dd.get_text(strip=True).replace("\n", " ").replace("\r", " ") if dd else ""
                # URL
                a = dl.find("a")
                href = a.get("href") if a else ""
                full_url = urljoin("https://www.thebell.co.kr/free/content/", href)

                if title:
                    titles.append(title)
                    bodies.append(body)
                    urls.append(full_url)
                    has_today = True
                    print(f"  - {title}")

            if not has_today and page > 1:
                print(f"  페이지 {page} 이후 오늘 기사 없음 → 종료")
                break
            if not items:
                break

            page += 1
            time.sleep(0.7)
        except Exception as e:
            print(f"  페이지 {page} 오류: {e}")
            break

    # ---------- CSV 생성 (메모리) ----------
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "Title", "Body", "Hyperlink"])

    for url, title, body in zip(urls, titles, bodies):
        safe_url = quote(url, safe=":/?=&%#")
        hyperlink = f'=HYPERLINK("{safe_url}", "{title.replace('"', '""')}")'
        writer.writerow([url, title, body, hyperlink])

    # DataFrame 으로 반환 (CSV 저장 로직은 index.py 에서 처리)
    import pandas as pd
    df = pd.read_csv(io.StringIO(output.getvalue()))
    return df
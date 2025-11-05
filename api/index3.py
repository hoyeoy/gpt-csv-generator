from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
import time
import urllib.parse
from pytz import timezone

app = Flask(__name__)

# ===============================
# 🔧 기본 설정
# ===============================
YESTERDAY = (datetime.now(timezone('Asia/Seoul')) - timedelta(days=1)).strftime('%Y-%m-%d')
TODAY = datetime.now(timezone('Asia/Seoul')).strftime('%Y-%m-%d')
#YESTERDAY = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
#TODAY = datetime.now().strftime('%Y-%m-%d')
"""YESTERDAY = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
TODAY = (datetime.now() - timedelta(days=1))"""

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

TITLE_KEYWORDS = ['투자', '유치', '선정', '지원금', '시리즈', '스타트업']


# ===============================
# 🧩 Part 1: 스타트업리시피 기업 추출
# ===============================
def crawl_startup_invest():
    url = "https://startuprecipe.co.kr/invest"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 사이트 접속 실패: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'lxml')
    tbody = soup.find('tbody')
    if not tbody:
        print("⚠️ tbody를 찾을 수 없습니다.")
        return pd.DataFrame()

    rows = tbody.find_all('tr')
    results = []

    for row in rows:
        cols = row.find_all('td')
        """if len(cols) < 5:
            continue"""

        date_text = cols[0].get_text(strip=True)
        company_text = cols[1].get_text(strip=True)
        stage_text = cols[4].get_text(strip=True)

        if date_text != YESTERDAY:
            continue
        if '인수합병' in stage_text:
            continue

        company_name = re.sub(r'\s*\(.*?\)\s*', '', company_text)
        company_name = re.sub(r'[^\w가-힣&\s-]', '', company_name).strip()
        if not company_name:
            continue

        link = ''
        a_tag = cols[1].find('a')
        if a_tag and a_tag.get('href'):
            href = a_tag['href']
            link = 'https://startuprecipe.co.kr' + href if href.startswith('/') else href

        results.append({
            'company': company_name,
            'stage': stage_text,
            'startup_link': link
        })

    df = pd.DataFrame(results).drop_duplicates(subset=['company'])

    # 내부 처리에는 pandas 사용
    df["company"] = df["company"].str.strip()
    # 리턴할 때만 변환
    return df.to_dict(orient="records")


# ===============================
# 📰 Part 2: 구글 뉴스 검색
# ===============================
def search_google_news_for_company(company_name):
    query = f'"{company_name}"'
    params = {
        'q': query,
        'tbs': 'qdr:d',  # 최근 1일
        'hl': 'ko',
        'gl': 'kr',
        'num': 10
    }

    search_url = 'https://news.google.com/search?' + urllib.parse.urlencode(params)

    try:
        time.sleep(1.2)
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        article_links = soup.find_all('a', href=True)
        for a in article_links:
            title_tag = a.find(['h3', 'h4']) or a
            title_text = title_tag.get_text(strip=True)
            if len(title_text) < 5:
                continue

            if any(keyword in title_text for keyword in TITLE_KEYWORDS):
                raw_link = a['href']
                if raw_link.startswith('./'):
                    link = 'https://news.google.com' + raw_link[1:]
                elif raw_link.startswith('/'):
                    link = 'https://news.google.com' + raw_link
                elif '/url?q=' in raw_link:
                    link = urllib.parse.unquote(raw_link.split('/url?q=')[1].split('&')[0])
                else:
                    link = raw_link

                return {'title': title_text, 'link': link}
        return {'title': None, 'link': None}
    except Exception as e:
        print(f"❌ 뉴스 검색 실패 ({company_name}): {e}")
        return {'title': None, 'link': None}


# ===============================
# 🚀 Flask 엔드포인트
# ===============================
@app.route("/api/startuprecipe", methods=["GET"])
@app.route("/api/startuprecipe", methods=["GET"])
def crawl_startuprecipe():
    """
    GET /api/startuprecipe
    → 어제 날짜 기준 스타트업리시피 투자 기사 + 관련 구글뉴스 결과를 JSON으로 반환
    """
    companies = crawl_startup_invest()  # ✅ list[dict] 반환

    if not companies:   # ✅ list는 빈 경우 이렇게 검사
        return jsonify({
            "date_range": f"{YESTERDAY} ~ {TODAY}",
            "count": 0,
            "articles": [],
            "message": "No news for yesterday."
        })

    results = []
    for company_info in companies:  # ✅ list 요소는 dict
        company = company_info['company']
        print(f"🔎 {company} 뉴스 검색 중...")
        news = search_google_news_for_company(company)

        results.append({
            "company": company,
            "stage": company_info['stage'],
            "startup_link": company_info['startup_link'],
            "news_title": news['title'],
            "news_link": news['link']
        })

    return jsonify({
        "date_range": f"{YESTERDAY} ~ {TODAY}",
        "count": len(results),
        "articles": results
    })


"""@app.route("/api/startuprecipe/debug")
def debug_request():
    try:
        resp = requests.get("https://startuprecipe.co.kr/invest", headers=headers, timeout=10)
        return jsonify({
            "status_code": resp.status_code,
            "html_snippet": resp.text[:500]
        })
    except Exception as e:
        return jsonify({"error": str(e)})"""
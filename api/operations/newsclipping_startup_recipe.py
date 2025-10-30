import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re
import time
import urllib.parse

# =============================================================================
# 설정
# =============================================================================
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
TODAY = datetime.now().strftime('%Y-%m-%d')
print(f"검색 대상 날짜: {YESTERDAY} ~ {TODAY}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
}

# 키워드 리스트 (제목에 포함되어야 함)
TITLE_KEYWORDS = ['투자', '유치', '선정', '지원금', '시리즈']

# =============================================================================
# PART 1: startuprecipe.co.kr 크롤링 (전처리)
# =============================================================================
def crawl_startup_invest():
    url = "https://startuprecipe.co.kr/invest"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"사이트 접속 실패: {e}")
        return pd.DataFrame()

    soup = BeautifulSoup(response.text, 'lxml')
    tbody = soup.find('tbody')
    if not tbody:
        print("tbody를 찾을 수 없습니다.")
        return pd.DataFrame()

    rows = tbody.find_all('tr')
    results = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue

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
    csv_filename = f'startuprecipe_news_{YESTERDAY}.csv'
    #df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
    print(f"전처리 완료: {len(df)}개 기업 추출")
    return df

# =============================================================================
# PART 2: 구글 뉴스 검색 - 회사명 검색 후 제목 키워드 필터링
# =============================================================================
def search_google_news_for_company(company_name):
    """
    1. 회사명으로 구글 뉴스 검색 (최근 1일)
    2. 결과 기사 중 제목에 TITLE_KEYWORDS 포함된 첫 번째 기사 반환
    """
    query = f'"{company_name}"'  # 회사명만 검색
    params = {
        'q': query,
        'tbs': 'qdr:d',  # 최근 1일
        'hl': 'ko',
        'gl': 'kr',
        'num': 10        # 최대 10개 요청 → 필터링
    }
    
    search_url = 'https://news.google.com/search?' + urllib.parse.urlencode(params)
    
    try:
        time.sleep(1.5)
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        # 모든 기사 링크 찾기
        article_links = soup.find_all('a', href=True)
        
        for a in article_links:
            # 제목 추출 (h3, h4, div 등 가능)
            title_tag = a.find(['h3', 'h4']) or a
            title_text = title_tag.get_text(strip=True)
            
            if len(title_text) < 5:
                continue

            # 제목에 키워드 포함 여부 확인
            if any(keyword in title_text for keyword in TITLE_KEYWORDS):
                # 링크 정제
                raw_link = a['href']
                if raw_link.startswith('./'):
                    link = 'https://news.google.com' + raw_link[1:]
                elif raw_link.startswith('/'):
                    link = 'https://news.google.com' + raw_link
                elif '/url?q=' in raw_link:
                    link = urllib.parse.unquote(raw_link.split('/url?q=')[1].split('&')[0])
                else:
                    link = raw_link

                return {
                    'title': title_text,
                    'link': link
                }
        
        return {'title': None, 'link': None}
    
    except Exception as e:
        print(f"뉴스 검색 실패 ({company_name}): {e}")
        return {'title': None, 'link': None}

# =============================================================================
# MAIN
# =============================================================================
df_companies = crawl_startup_invest()

if df_companies.empty:
    print("추출된 기업 없음. 종료.")
else:
    print("\n구글 뉴스 검색 시작 (회사명 검색 → 제목 키워드 필터)...\n")
    results = []

    for idx, row in df_companies.iterrows():
        company = row['company']
        print(f"[{idx+1}/{len(df_companies)}] 검색: {company}", end=" → ")
        
        news = search_google_news_for_company(company)
        
        title_preview = (news['title'][:50] + '...') if news['title'] else '없음'
        print(title_preview)

        hyperlink = f'=HYPERLINK("{news['link']}", "{news['title']}")'
        
        results.append({
            'company': company,
            'news_title': news['title'],
            'news_link': news['link'],
            'hyperlink' : hyperlink
        })

    # 최종 저장
    df_final = pd.DataFrame(results)
    final_csv = f'startuprecipe_news_{YESTERDAY}.csv'
    df_final.to_csv(final_csv, index=False, encoding='utf-8-sig')

    print(f"\n완료! {len(df_final)}건 처리 → {final_csv}")
    print("\n결과 요약:")
    for _, r in df_final.iterrows():
        status = "발견" if r['news_title'] else "미발견"
        print(f"  • {r['company']} → {status}")
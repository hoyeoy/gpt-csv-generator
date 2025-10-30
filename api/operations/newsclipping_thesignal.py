import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from urllib.parse import urljoin
from urllib.parse import quote
import csv

def save_to_csv_with_hyperlink(titles, bodies, urls, filename=None):
    """
    titles: list[str]
    bodies: list[str]
    urls:   list[str]
    → CSV 저장 + Hyperlink 컬럼 추가 (엑셀에서 클릭 가능)
    """
    if len(titles) != len(bodies) or len(titles) != len(urls):
        raise ValueError("모든 리스트 길이가 동일해야 합니다.")

    if not filename:
        today = datetime.now().strftime('%Y%m%d')
        filename = f"sedaily_news_{today}.csv"

    # 엑셀에서 인식하는 HYPERLINK 공식: =HYPERLINK("URL", "텍스트")
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # 헤더
        writer.writerow(['URL', 'Title', 'Body', 'Hyperlink'])
        
        # 데이터
        for url, title, body in zip(urls, titles, bodies):
            # URL 인코딩 (특수문자 방지)
            safe_url = quote(url, safe=':/?=&%#')
            # 하이퍼링크 공식 (엑셀에서 바로 클릭 가능)
            hyperlink = f'=HYPERLINK("{safe_url}", "{title.replace('"', '""')}")'
            
            writer.writerow([url, title, body, hyperlink])
    
    print(f"CSV 저장 완료: {filename}")
    print(f"   → 총 {len(titles)}건")
    print(f"   → 엑셀에서 'Hyperlink' 컬럼 클릭하면 바로 이동!")

def get_todays_news_titles():
    """
    signal.sedaily.com 실시간 뉴스에서 오늘 게시된 기사 제목만 추출
    HTML 구조를 사이트에 맞게 조정: 가정된 구조 - <li class="article_list_item"><a href="..."><h3 class="title">제목</h3></a><p class="summary">요약</p><span class="date">날짜</span></li>
    실제 구조에 맞게 선택자 조정 필요 (브라우저 개발자 도구로 확인)
    """
    today_str = datetime.now().strftime('%Y-%m-%d')  # "2025-10-27"
    titles = []
    bodies = []
    urls = []
    page = 1
    max_pages = 50
    
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
        )
    }
    
    print(f"🔍 {today_str} 게시 기사 수집 시작...")
    
    base_url = "https://signal.sedaily.com/NewsList/GX11"
    
    while page <= max_pages:
        url = f"{base_url}/page/{page}"  # 페이지네이션 형식 가정 (실제 확인 필요, ?page={page} 일 수 있음)
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # ✅ 기사 아이템 선택자: 사이트 구조에 맞게 조정 (e.g., 'li' or 'div', class='article_list_item' 등)
            article_items = soup.find_all('li', class_='article_list_item')  # 클래스 이름 실제로 확인 필요
            
            if not article_items:
                # 대안 선택자 시도
                article_items = soup.find_all('div', class_='news_item')  # 다른 클래스 가정
            if not article_items:
                article_items = soup.find_all('li')  # 모든 li fallback
            
            page_has_today = False
            for item in article_items:
                # 1. 날짜 추출
                date_span = item.find('span', class_='date')  # 클래스 이름 실제 확인
                if not date_span:
                    continue
                
                date_text = date_span.get_text(strip=True)  # e.g., "2025-10-27 08:14"
                
                # 오늘 날짜와 매칭 (시작 부분 매칭)
                if not date_text.startswith(today_str):
                    continue
                
                # 2. 제목 추출: <h3> or <a> 태그 등
                title_tag = item.find('h3', class_='title') or item.find('a', class_='title') or item.find('h3') or item.find('a')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                if title:
                    titles.append(title)
                    page_has_today = True
                    # print(f"✅ [{page}페이지] {title}")

                # 3. 요약 추출: <p class="summary"> or <div class="excerpt"> 등
                body_tag = item.find('p', class_='summary') or item.find('div', class_='body') or item.find('p')
                if not body_tag:
                    body = ''  # 요약 없으면 빈 문자열
                else:
                    body = body_tag.get_text(strip=True)
                    body = body.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                
                bodies.append(body)
                
                # 4. 링크 추출: <a> 태그 href
                a_tag = item.find('a', href=True)
                if not a_tag:
                    continue
                
                href = a_tag.get('href')
                if not href:
                    continue
                
                full_url = urljoin(base_url, href)
                urls.append(full_url)
                print(f"✅ [{page}페이지] {title} {full_url}")
            
            # 현재 페이지에 오늘 기사가 없으면 종료 (최적화)
            if not page_has_today and page > 1:
                print(f"⏹️  {page}페이지 이후 오늘 기사 없음 → 종료")
                break
            
            if not article_items:
                print(f"⏹️  {page}페이지: 기사 없음 → 종료")
                break
                
            print(f"📄 {page}페이지 완료 (총 {len(titles)}건)")
            page += 1
            time.sleep(0.7)  # 서버 부하 방지
            
        except requests.RequestException as e:
            print(f"❌ {page}페이지 오류: {e}")
            break
    
    return titles

# 실행
if __name__ == "__main__":
    titles = []
    bodies = []
    urls = []

    today_titles = get_todays_news_titles()
    
    print("\n" + "="*60)
    print(f"🎉 {datetime.now().strftime('%Y-%m-%d')} 총 {len(today_titles)}건 뉴스")
    print("="*60)
    
    for i, title in enumerate(today_titles, 1):
        print(f"{i:2d}. {title}")
    
    print("\n✅ 완료!")

    # CSV 저장 + 하이퍼링크 추가
    save_to_csv_with_hyperlink(titles, bodies, urls)

    print("\n✅ csv 파일 생성 완료!")
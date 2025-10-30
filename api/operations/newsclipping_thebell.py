import time
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd


def run(params: dict = None) -> pd.DataFrame:
    """
    TheBell 뉴스 사이트에서 지정된 날짜의 기사를 수집합니다.
    
    params:
        - days_ago: int (기본값 1, 어제 날짜)
    반환: pandas.DataFrame (URL, Title, Summary 컬럼 포함)
    """
    params = params or {}
    days_ago = params.get("days_ago", 1)
    
    # 🎯 target_date 포맷을 'YYYY-MM-DD'로 설정
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

    titles, bodies, urls = [], [], []
    page = 1
    max_pages = 5
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        )
    }

    print(f"[{target_date}] The Bell 뉴스 수집 시작")
    
    while page <= max_pages:
        url = f"https://www.thebell.co.kr/free/content/article.asp?page={page}&svccode=00"
        print(f"  페이지 {page}: {url}")

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # <li> 요소를 찾되, list_type이라는 클래스를 가진 div 안에서만 찾도록 범위를 좁힘 (더 안전함)
            list_container = soup.find('div', class_='list_type') 
            if not list_container:
                print(f"  페이지 {page}: 뉴스 목록 컨테이너 (list_type)를 찾을 수 없음")
                break
                
            items = list_container.find_all("li")
            if not items:
                print(f"  페이지 {page}: 기사 항목이 없음 → 종료")
                break
                
            has_target_date_article = False

            for li in items:
                dl = li.find("dl")
                if not dl:
                    continue
                    
                # 1. 날짜 추출 및 비교
                date_span = dl.find("span", class_="date")
                if not date_span:
                    continue
                
                date_text = date_span.get_text(strip=True) # 예: "2025-10-29 오전 8:14:35"
                
                # 'YYYY-MM-DD'로 시작하는지 확인 (가장 확실한 비교)
                if not date_text.startswith(target_date):
                    # target_date 기사가 아니면, 이 페이지 이후는 더 오래된 기사일 가능성이 높으므로 멈추지 않고 계속 진행
                    continue

                # 2. 제목 추출
                dt = dl.find("dt")
                title = dt.get_text(strip=True) if dt else ""

                # 3. 요약 추출
                dd = dl.find("dd")
                body = dd.get_text(strip=True).replace("\n", " ").replace("\r", " ") if dd else ""

                # 4. URL 추출 및 변환
                a = dl.find("a")
                href = a.get("href") if a else ""
                full_url = urljoin("https://www.thebell.co.kr/free/content/", href)

                # 5. 데이터 저장
                if title and full_url:
                    titles.append(title)
                    bodies.append(body)
                    urls.append(full_url)
                    has_target_date_article = True
                    print(f"    → {title}")
                
            # 최적화: 이 페이지에 target_date 기사가 하나도 없으면 다음 페이지는 더 오래된 기사일 가능성이 높음
            if not has_target_date_article and page > 1:
                print(f"  페이지 {page} 이후 {target_date} 기사 없음 → 종료")
                break

            page += 1
            time.sleep(0.7)

        except requests.RequestException as e:
            print(f"  페이지 {page} 요청 오류: {e}")
            break
        except Exception as e:
            print(f"  페이지 {page} 처리 오류: {e}")
            break

    # DataFrame 생성
    df = pd.DataFrame({
        "URL": urls,
        "Title": titles,
        "Summary": bodies
    })

    print(f"총 {len(df)}개 기사 수집 완료")
    return df

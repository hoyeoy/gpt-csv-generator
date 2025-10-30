import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from urllib.parse import urljoin, quote
import csv

# 4개 컬럼 CSV 저장 함수 (URL, Title, Body, Hyperlink)
def save_to_csv_with_hyperlink(titles, bodies, urls, filename=None):
    if len(titles) != len(bodies) or len(titles) != len(urls):
        raise ValueError("titles, bodies, urls의 길이가 동일해야 합니다.")

    if not filename:
        today = datetime.now().strftime('%Y%m%d')
        filename = f"investchosun_news_{today}.csv"

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Title', 'Body', 'Hyperlink'])
        
        for url, title, body in zip(urls, titles, bodies):
            safe_url = quote(url, safe=':/?=&%#')
            hyperlink = f'=HYPERLINK("{safe_url}", "{title.replace('"', '""')}")'
            writer.writerow([url, title, body, hyperlink])
    
    print(f"CSV 저장 완료: {filename}")
    print(f"   → 총 {len(titles)}건")
    print(f"   → 엑셀에서 'Hyperlink' 컬럼 클릭하면 바로 이동!")


def get_todays_investchosun_news():
    # today_str = datetime.now().strftime('%Y.%m.%d')  # "2025.10.27"
    today_str = (datetime.now() - timedelta(days=1)).strftime('%Y.%m.%d')
    titles = []
    bodies = []
    urls = []
    page = 1
    max_pages = 50

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
    }

    session = requests.Session()
    base_url = "https://www.investchosun.com/svc/news/list.html"

    print(f"[{today_str}] 인베스트조선 뉴스 수집 시작...")

    while page <= max_pages:
        params = {
            'catid': '2',
            'pn': str(page)
        }

        try:
            resp = session.get(base_url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 기사 목록: ul.list_ul > li
            article_items = soup.select('ul.list_ul > li')
            if not article_items:
                print(f"{page}페이지: 기사 없음 → 종료")
                break

            page_has_today = False

            for li in article_items:
                # 1. 제목 & 링크 (dt > a)
                dt = li.find('dt')
                if not dt:
                    continue
                a_tag = dt.find('a', href=True)
                if not a_tag:
                    continue

                title = a_tag.get_text(strip=True)
                relative_url = a_tag['href']
                full_url = urljoin("https://www.investchosun.com", relative_url)

                # 2. 본문 요약 (dd.summary > a)
                body = ""
                dd_summary = li.find('dd', class_='summary')
                if dd_summary:
                    summary_a = dd_summary.find('a')
                    if summary_a:
                        body = summary_a.get_text(strip=True)
                        # 불필요한 공백 제거 및 정리
                        body = ' '.join(body.split())
                    else:
                        body = dd_summary.get_text(strip=True)
                else:
                    body = ""

                # 3. 날짜 추출 (dd.date > span 첫 번째)
                dd_date = li.find('dd', class_='date')
                if not dd_date:
                    continue
                date_span = dd_date.find('span')
                if not date_span:
                    continue
                date_text = date_span.get_text(strip=True).strip()

                # 오늘 날짜와 비교
                if date_text != today_str:
                    continue

                # 중복 방지
                if full_url in urls:
                    continue

                # 저장
                titles.append(title)
                bodies.append(body)
                urls.append(full_url)
                page_has_today = True

                print(f"[{page}P] {title}")
                if len(body) > 80:
                    print(f"     요약: {body[:80]}...")
                else:
                    print(f"     요약: {body}")

            if not page_has_today and page > 1:
                print(f"{page}페이지 이후 오늘 기사 없음 → 종료")
                break

            print(f"{page}페이지 완료 (누적 {len(titles)}건)")
            page += 1
            time.sleep(0.8)

        except requests.RequestException as e:
            print(f"{page}페이지 요청 실패: {e}")
            break
        except Exception as e:
            print(f"파싱 오류: {e}")
            break

    return titles, bodies, urls


# 실행부
if __name__ == "__main__":
    titles, bodies, urls = get_todays_investchosun_news()

    print("\n" + "="*80)
    today_display = datetime.now().strftime('%Y-%m-%d')
    print(f"{today_display} 인베스트조선 뉴스 수집 완료 → 총 {len(titles)}건")
    print("="*80)
    
    for i, (title, body, url) in enumerate(zip(titles, bodies, urls), 1):
        print(f"{i:2d}. {title}")
        print(f"     요약: {body}")
        print(f"     {url}\n")

    # CSV 저장 (4개 컬럼)
    save_to_csv_with_hyperlink(titles, bodies, urls)

    print("CSV 파일 생성 완료!")
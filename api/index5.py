# readability-lxml를 활용해서 url 제공 시 뉴스 기사의 본문을 파싱하는 api 
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup
from readability import Document

app = Flask(__name__)

# ===============================
# 🔧 HEADERS 필수 추가!
# ===============================
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


@app.route("/api/parse_article", methods=["GET"])
def parse_article():
    """
    GET /api/parse_article?url=<뉴스_URL>
    → 제공된 뉴스 URL의 본문을 readability-lxml로 파싱하여 JSON으로 반환
    """
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    try:
        # URL에서 페이지 내용 가져오기
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = 'utf-8'  # 한글 깨짐 방지

        # readability-lxml로 본문 추출
        doc = Document(response.text)
        title = doc.title().strip()
        content_html = doc.summary()

        # HTML에서 순수 텍스트 추출
        soup = BeautifulSoup(content_html, 'html.parser')
        content_text = soup.get_text(separator=' ', strip=True)

        # 빈 결과 처리
        if not title or not content_text:
            return jsonify({"error": "기사 제목 또는 본문을 찾을 수 없습니다."}), 404

        return jsonify({
            "success": True,
            "title": title,
            "content": content_text,
            "url": url
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"URL 요청 오류: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"파싱 오류: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
# api/newsclipping_thesignal.py (테스트용 최소 코드)
import io
import csv


def handler(event, context=None):

    fieldnames = ["title", "link", "summary", "published_at"]

    # 테스트 데이터
    articles = [
        {"title": "Test Title", "link": "https://example.com", "summary": "Test summary", "published_at": "2025-10-31 12:00"}
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(articles)
    csv_content = output.getvalue()

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": "attachment; filename=test.csv"
        },
        "body": csv_content
    }


"""# api/index.py
import os
import uuid
import importlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font

app = FastAPI()
TEMP_DIR = "/tmp/csv_files"
os.makedirs(TEMP_DIR, exist_ok=True)


class CSVRequest(BaseModel):
    operation: str
    params: Dict[str, Any] = {}
    format: str = "csv"  # "csv" or "xlsx"


def load_operation(op: str):
    try:
        mod = importlib.import_module(f".operations.{op}", package="api")
        if not hasattr(mod, "run"):
            raise ValueError("run() 함수가 없습니다.")
        return mod.run
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"작업 로드 실패: {e}")


@app.get("/")
async def root():
    return {
        "message": "CSV/XLSX Generator API",
        "endpoints": ["/generate", "/health", "/download/..."]
    }


@app.get("/health")
async def health():
    return {"status": "OK", "time": datetime.now().isoformat()}


@app.get("/download/{filename}")
async def download(filename: str):
    path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    return FileResponse(path, filename=filename)


@app.post("/generate")
async def generate(req: CSVRequest):
    try:
        run_fn = load_operation(req.operation)
        df = run_fn(req.params)  # DataFrame 수신

        if df.empty:
            return JSONResponse({"message": "수집된 데이터 없음", "rows": 0})

        # 고유 파일명 생성
        ext = "xlsx" if req.format == "xlsx" else "csv"
        filename = f"{req.operation}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(TEMP_DIR, filename)

        # 저장
        if req.format == "xlsx":
            # XLSX 저장 + 하이퍼링크
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='News')
                worksheet = writer.sheets['News']

                # URL 열에 하이퍼링크 적용 (B열)
                for row in range(2, len(df) + 2):
                    cell = worksheet.cell(row=row, column=1)  # URL 열
                    if cell.value:
                        cell.hyperlink = cell.value
                        cell.style = "Hyperlink"
                        cell.font = Font(color="0000FF", underline="single")

        else:
            # CSV 저장
            df.to_csv(filepath, index=False, encoding="utf-8-sig")

        # 다운로드 URL
        base_url = os.getenv('VERCEL_URL', 'your-app.vercel.app')
        download_url = f"https://{base_url}/download/{filename}"

        return JSONResponse({
            "message": f"{req.operation} 완료!",
            "rows": len(df),
            "format": req.format.upper(),
            "download_url": download_url,
            "expires_in": "30분 후 자동 삭제"
        })

    except Exception as e:
        raise HTTPException(500, detail=f"처리 중 오류: {str(e)}")"""
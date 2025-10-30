# api/index.py
import os
import uuid
import importlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime 

app = FastAPI()
TEMP_DIR = "/tmp/csv_files"
os.makedirs(TEMP_DIR, exist_ok=True)


class CSVRequest(BaseModel):
    operation: str                     # 예: "thebell_news"
    params: Dict[str, Any] = {}        # 추가 파라미터 (days_ago 등)


def load_operation(op: str):
    try:
        mod = importlib.import_module(f".operations.{op}", package="api")
        if not hasattr(mod, "run"):
            raise ValueError("run() 함수 없음")
        return mod.run
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"작업 로드 실패: {e}")


@app.get("/download/{filename}")
async def download(filename: str):
    path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "파일 없음")
    return FileResponse(path, media_type="text/csv", filename=filename)


@app.post("/generate")
async def generate(req: CSVRequest):
    try:
        run_fn = load_operation(req.operation)
        df = run_fn(req.params)                     # <-- 여기서 스크래핑 실행

        filename = f"{req.operation}_{uuid.uuid4().hex[:8]}.csv"
        filepath = os.path.join(TEMP_DIR, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")

        download_url = f"https://{os.getenv('VERCEL_URL', 'your-app.vercel.app')}/api/download/{filename}"

        return JSONResponse({
            "message": f"{req.operation} 완료!",
            "rows": len(df),
            "download_url": download_url,
            "expires_in": "30분 후 자동 삭제"
        })
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# api/index.py (맨 아래에 추가)

@app.get("/")
async def root():
    return {"message": "CSV Generator API 실행 중", "endpoints": ["/generate", "/health", "/download/..."]}

@app.get("/health")
async def health():
    return {"status": "OK", "time": datetime.now().isoformat()}
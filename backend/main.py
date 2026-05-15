import io
import json
from urllib.parse import quote

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openpyxl import load_workbook

from executor import execute_mapping
from llm_parser import parse_rules


app = FastAPI(title="Excel 字段映射填充工具")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Execute-Log", "Content-Disposition"],
)


def _validate_xlsx(upload: UploadFile, label: str) -> None:
    name = (upload.filename or "").lower()
    if not name.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=f"{label} 必须是 .xlsx 文件")


async def _read_bytes(upload: UploadFile) -> bytes:
    data = await upload.read()
    await upload.seek(0)
    return data


@app.post("/api/sheets")
async def get_sheets(
    user_file: UploadFile = File(...),
    sys_file: UploadFile = File(...),
):
    _validate_xlsx(user_file, "用户表")
    _validate_xlsx(sys_file, "系统表")

    user_bytes = await _read_bytes(user_file)
    sys_bytes = await _read_bytes(sys_file)

    try:
        user_wb = load_workbook(io.BytesIO(user_bytes), read_only=True, data_only=True)
        sys_wb = load_workbook(io.BytesIO(sys_bytes), read_only=True, data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取 Excel 失败: {e}")

    return {
        "user_sheets": user_wb.sheetnames,
        "sys_sheets": sys_wb.sheetnames,
    }


@app.post("/api/execute")
async def execute(
    user_file: UploadFile = File(...),
    sys_file: UploadFile = File(...),
    user_sheet: str = Form(...),
    sys_sheet: str = Form(...),
    rules: str = Form(...),
):
    _validate_xlsx(user_file, "用户表")
    _validate_xlsx(sys_file, "系统表")

    if not rules.strip():
        raise HTTPException(status_code=400, detail="规则文本不能为空")

    user_bytes = await _read_bytes(user_file)
    sys_bytes = await _read_bytes(sys_file)

    try:
        user_df = pd.read_excel(io.BytesIO(user_bytes), sheet_name=user_sheet)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取用户表失败: {e}")

    user_headers = [str(c) for c in user_df.columns.tolist()]

    try:
        sys_wb = load_workbook(io.BytesIO(sys_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"读取系统表失败: {e}")

    if sys_sheet not in sys_wb.sheetnames:
        raise HTTPException(status_code=400, detail=f"系统表中不存在 Sheet「{sys_sheet}」")

    sys_ws = sys_wb[sys_sheet]
    sys_headers = [cell.value for cell in sys_ws[1]]

    try:
        config = parse_rules(user_headers, sys_headers, rules)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"规则解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用 LLM 失败: {e}")

    key_mapping = config.get("key_mapping") or {}
    if not key_mapping.get("user_col") or not key_mapping.get("sys_col"):
        raise HTTPException(status_code=400, detail="规则中未声明主键，请补充「主键：用户表[列] 对应 系统表[列]」")

    try:
        sys_wb, log = execute_mapping(config, user_df, sys_wb, sys_sheet)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = io.BytesIO()
    sys_wb.save(out)
    out.seek(0)

    log_json = json.dumps(log, ensure_ascii=False, default=str)
    headers = {
        "X-Execute-Log": quote(log_json),
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote("系统表_已填充.xlsx"),
    }
    return StreamingResponse(
        out,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )

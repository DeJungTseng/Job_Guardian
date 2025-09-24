# job-guardian/mcp_server/server.py
# MCP server: tools = esg_hr, labor_violations, ge_work_equality_violations
# 每次 tool call 直接從官方 URL 下載最新 CSV，於工具內做 ETL/篩選/回傳。
# 參考 mcp-agent 的 asyncio/fastmcp 範例（@mcp.tool）

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import time
import unicodedata
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import socket
import requests.packages.urllib3.util.connection as urllib3_cn


def _force_ipv4():
    def allowed_gai_family():
        return socket.AF_INET
    urllib3_cn.allowed_gai_family = allowed_gai_family


_force_ipv4()


# ------------------------------------------------------------
# 初始化
# ------------------------------------------------------------
load_dotenv()
mcp = FastMCP("job-guardian")

# 來源 URL（可用 .env 覆寫）
ESG_URL = os.getenv(
    "ESG_URL",
    "https://mopsfin.twse.com.tw/opendata/t187ap46_O_5.csv",
).strip()

LAB_VIO_URL = os.getenv(
    "LAB_VIO_URL",
    "https://apiservice.mol.gov.tw/OdService/download/A17000000J-030225-svj",
).strip()

GE_VIO_URL = os.getenv(
    "GE_VIO_URL",
    "https://apiservice.mol.gov.tw/OdService/download/A17000000J-030226-sop",
).strip()

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
CASE_SENSITIVE = os.getenv("CASE_SENSITIVE", "false").lower() == "true"
PARTIAL_MATCH = os.getenv(
    "PARTIAL_MATCH", "false").lower() == "true"  # True: 子字串/模糊包含

# ------------------------------------------------------------
# 公用：時間/名稱正規化/CSV下載與解析
# ------------------------------------------------------------


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


SUFFIX_PAT = re.compile(r"(股份有?限公司|有限?公司|公司|Co\.?,?Ltd\.?)$")


def normalize_company_name(name: str) -> str:
    """去括號/空白/常見尾綴；NFKC 正規化。"""
    if not name:
        return ""
    s = unicodedata.normalize("NFKC", str(name)).strip()
    s = re.sub(r"（.*?）|\(.*?\)", "", s)
    s = re.sub(r"\s+", "", s)
    s = SUFFIX_PAT.sub("", s)
    return s


def _fetch_csv_rows(url: str) -> List[Dict[str, str]]:
    """
    下載 CSV → DictReader。
    先嘗試 requests (UA 模擬 curl)，若失敗再 fallback httpx。
    """
    import httpx

    # 嘗試多種解碼
    def _decode_content(content: bytes) -> str:
        for enc in ("utf-8", "cp950", "big5", "latin-1"):
            try:
                return content.decode(enc)
            except UnicodeDecodeError:
                continue
        # 全部失敗就回傳 binary
        return content.decode("utf-8", errors="ignore")

    # ---------- 1. 先用 requests ----------
    try:
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": "curl/8.5.0",
                "Accept": "text/csv,*/*;q=0.8",
            },
        )
        resp.raise_for_status()
        text = _decode_content(resp.content)
        rows = list(csv.DictReader(io.StringIO(text)))
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in rows]

    except Exception as e_req:
        print(f"[WARN] requests 抓取失敗，改用 httpx: {e_req}")

    # ---------- 2. fallback httpx ----------
    try:
        with httpx.Client(
            http2=False,
            timeout=HTTP_TIMEOUT,
            headers={
                "User-Agent": "curl/8.5.0",
                "Accept": "text/csv,*/*;q=0.8",
            },
            transport=httpx.HTTPTransport(local_address="0.0.0.0")
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
            text = _decode_content(resp.content)
            rows = list(csv.DictReader(io.StringIO(text)))
            return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in rows]

    except Exception as e_httpx:
        raise RuntimeError(f"requests + httpx 都無法抓取 {url}: {e_httpx}")


def _match_company(row_value: str, user_input: str) -> bool:
    """依環境變數設定做精確/包含比對，並處理大小寫與名稱正規化。"""
    if not CASE_SENSITIVE:
        row_value = row_value.lower()
        user_value = user_input.lower()
    else:
        user_value = user_input

    # 也跑一次正規化（中英文公司尾綴/空白）
    row_norm = normalize_company_name(row_value)
    user_norm = normalize_company_name(user_value)

    if PARTIAL_MATCH:
        return (user_value in row_value) or (user_norm in row_norm)
    else:
        return (row_value == user_value) or (row_norm == user_norm)


def _pick(d: Dict[str, str], *candidates: str) -> Optional[str]:
    """從多個候選欄名中拿第一個存在的值。"""
    for k in candidates:
        if k in d and d[k] != "":
            return d[k]
    return None


# ------------------------------------------------------------
# Tool 1: esg_hr（ESG 人力發展）
#   來源：t187ap46_O_5.csv
#   常見欄位（可能因年版不同略有差異）：
#   - 公司代號, 公司名稱, 申報年度/年度
#   - 員工薪資中位數/薪資中位數, 員工薪資平均數/薪資平均數
#   - 女性主管比例/女性主管比, 福利（視資料而定）
# ------------------------------------------------------------
@mcp.tool()
def esg_hr(company: str, year: Optional[int] = None, limit: int = 50) -> dict:
    """
    查 ESG 人力發展（薪資/福利/女性主管比等）。會即時抓取 CSV，於工具內 ETL 後回傳。
    Args:
      company: 公司名稱（可含股份有限公司等尾綴）
      year: 指定年度（可省略）
      limit: 最多回傳筆數
    Returns: dict(items=[...], source_url, fetched_at, meta)
    """
    rows = _fetch_csv_rows(ESG_URL)
    out: List[Dict[str, str | float | int]] = []

    for r in rows:
        comp = _pick(r, "公司名稱", "公司", "公司名稱(中)", "company", "CompanyName")
        if not comp:
            continue
        if not _match_company(comp, company):
            continue

        y = _pick(r, "申報年度", "年度", "Year", "year", "報告年度")
        if year is not None and (str(year) != str(y)):
            continue

        item = {
            "公司代號": _pick(r, "公司代號", "股票代號", "StockCode"),
            "公司名稱": comp,
            "年度": y,
            "員工薪資中位數": _pick(
                r,
                "員工薪資中位數",
                "薪資中位數",
                "MedianSalary",
                "薪資中位",
                "非擔任主管之全時員工薪資中位數(仟元/人)",
            ),
            "員工薪資平均數": _pick(
                r,
                "員工薪資平均數",
                "薪資平均數",
                "AverageSalary",
                "薪資平均",
                "員工薪資平均數(仟元/人)",
            ),
            "女性主管比例": _pick(
                r,
                "女性主管比例",
                "女性主管比",
                "FemaleManagerRatio",
                "管理職女性主管佔比",
            ),
            "資料列原始": r,
        }
        out.append(item)
        if len(out) >= limit:
            break

    return {
        "items": out,
        "count": len(out),
        "source_url": ESG_URL,
        "fetched_at": _iso_now(),
        "meta": {"query": company, "year": year, "partial_match": PARTIAL_MATCH},
    }


# ------------------------------------------------------------
# Tool 2: labor_violations（違反勞基法）
#   來源：A17000000J-030225-svj
#   推測欄位：
#   - 事業單位名稱, 所在縣市, 違反法條, 違反法條內容, 公告日期, 裁處機關, 罰鍰金額
# ------------------------------------------------------------
@mcp.tool()
def labor_violations(company: str, since_year: Optional[int] = None, limit: int = 50) -> dict:
    """
    查勞動部違反勞基法紀錄（官方彙總）。
    Args:
      company: 事業單位名稱（可用部分關鍵字）
      since_year: 公告日期的年份 >= since_year 才算
      limit: 最多回傳筆數
    """
    rows = _fetch_csv_rows(LAB_VIO_URL)
    out: List[Dict[str, str]] = []
    by_year: Dict[str, int] = {}

    for r in rows:
        comp = _pick(r, "事業單位名稱或負責人", "事業單位名稱", "雇主名稱", "公司名稱", "name")
        if not comp:
            continue

        # 支援部分關鍵字比對（公司名包含即可）
        if company not in comp:
            continue

        # 公告日期
        date = _pick(r, "公告日期", "公布日期", "處分日期", "date", "公告日")
        y = (date or "")[:4]

        # 年份過濾
        if since_year is not None and (not y.isdigit() or int(y) < int(since_year)):
            continue

        item = {
            "事業單位名稱": comp,
            "公告日期": date,
            "裁處機關": _pick(r, "主管機關", "裁處機關", "機關"),
            "違反法條": _pick(r, "違法法規法條", "違反法條", "法條"),
            "違反法條內容": _pick(r, "違反法規內容", "違反法條內容", "違規內容", "事實摘要"),
            "罰鍰金額": _pick(r, "罰鍰金額", "處分金額", "金額"),
            "資料列原始": r,
        }
        out.append(item)

        if y:
            by_year[y] = by_year.get(y, 0) + 1

        if len(out) >= limit:
            break

    return {
        "items": out,
        "count": len(out),
        "stats": {"count_by_year": by_year},
        "source_url": LAB_VIO_URL,
        "fetched_at": _iso_now(),
        "meta": {"query": company, "since_year": since_year, "partial_match": True},
    }


# ------------------------------------------------------------
# Tool 3: ge_work_equality_violations（違反性平工作法）
#   來源：A17000000J-030226-sop
#   常見欄位：
#   - 事業單位名稱, 違反法條, 違反法條內容, 公告日期, 裁處機關
# ------------------------------------------------------------
@mcp.tool()
def ge_work_equality_violations(
    company: str, since_year: Optional[int] = None, limit: int = 50) -> dict:
    """
    查性平工作法違規紀錄（官方彙總）。
    Args:
      company: 公司名稱或關鍵字
      since_year: 公告日期包含該年份字串 (ex: 2025)
      limit: 最多回傳筆數
    """
    rows = _fetch_csv_rows(GE_VIO_URL)
    out: List[Dict[str, str]] = []
    by_year: Dict[str, int] = {}

    for r in rows:
        # ⚡ 修正公司欄位
        comp = _pick(r, "事業單位名稱或負責人", "事業單位名稱", "雇主名稱", "公司名稱", "name")
        if not comp:
            continue

        # ⚡ 改用模糊比對
        if company not in comp:
            continue

        date = _pick(r, "公告日期", "公布日期", "處分日期", "date")
        y = (date or "")[:4]

        # ⚡ 改為「字串包含」模式
        if since_year is not None and str(since_year) not in (date or ""):
            continue

        item = {
            "事業單位名稱": comp,
            "公告日期": date,
            "裁處機關": _pick(r, "主管機關", "裁處機關", "機關"),
            "違反法條": _pick(r, "違法法規法條", "違反法條", "法條"),
            "違反法條內容": _pick(r, "違反法規內容", "違反法條內容", "違規內容", "事實摘要"),
            "罰鍰金額": _pick(r, "罰鍰金額", "處分金額", "金額"),
            "資料列原始": r,
        }
        out.append(item)

        if y:
            by_year[y] = by_year.get(y, 0) + 1

        if len(out) >= limit:
            break

    return {
        "items": out,
        "count": len(out),
        "stats": {"count_by_year": by_year},
        "source_url": GE_VIO_URL,
        "fetched_at": _iso_now(),
        "meta": {"query": company, "since_year": since_year, "partial_match": True},
    }

# ------------------------------------------------------------
# Server Entrypoint
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", type=str, default=None,
                        help="Run HTTP/SSE. Example: 127.0.0.1:7332")
    parser.add_argument("--transport", type=str, default=None,
                        choices=["stdio", "http", "sse"],
                        help="Override transport explicitly")
    args = parser.parse_args()

    # 優先用 --transport；其次，如果有 --http，就用 http
    if args.transport:
        if args.transport == "stdio":
            # STDIO 不需要 host/port
            print("Running on STDIO")
            mcp.run(transport="stdio")

        elif args.transport in ("http", "sse"):
            host, port = (args.http or "127.0.0.1:7332").split(":")
            print(f"Running on {args.transport} at http://{host}:{port}")
            mcp.run(transport=args.transport, host=host, port=int(port))

    elif args.http:
        host, port = args.http.split(":")
        print(f"Running on HTTP at http://{host}:{port}")
        mcp.run(transport="http", host=host, port=int(port))
    else:
        # 預設走 STDIO
        print("Running on STDIO")
        mcp.run()  # 等同 mcp.run(transport="stdio")

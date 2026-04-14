"""
脱口秀演出票务 MCP Server
基于有赞开放平台 API
"""
import json
import os
import time
import hashlib
import requests
from http.server import BaseHTTPRequestHandler

# 有赞 API 配置（从环境变量读取）
CLIENT_ID = os.environ.get("YOUZAN_CLIENT_ID", "YOUR_CLIENT_ID")
CLIENT_SECRET = os.environ.get("YOUZAN_CLIENT_SECRET", "YOUR_CLIENT_SECRET")
KDT_ID = os.environ.get("YOUZAN_KDT_ID", "YOUR_KDT_ID")  # 店铺ID

YOUZAN_TOKEN_URL = "https://open.youzanyun.com/auth/token"
YOUZAN_API_URL = "https://open.youzanyun.com/api"

_token_cache = {"token": None, "expires_at": 0}


def get_access_token():
    """获取有赞 access_token，带缓存"""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    resp = requests.post(YOUZAN_TOKEN_URL, json={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "silent",
        "authorize_type": "self",
    })
    data = resp.json()
    token = data.get("data", {}).get("access_token")
    expires_in = data.get("data", {}).get("expires_in", 7200)
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


def youzan_api(api_name, version, params=None):
    """调用有赞 API"""
    token = get_access_token()
    url = f"{YOUZAN_API_URL}/{api_name}/{version}"
    resp = requests.get(url, params={
        "access_token": token,
        "kdt_id": KDT_ID,
        **(params or {})
    })
    return resp.json()


# ── MCP 工具函数 ────────────────────────────────────────────

def get_shows(arguments: dict) -> str:
    """获取近期演出列表"""
    data = youzan_api("youzan.items.onsale.get", "3.0.0", {
        "page_no": 1,
        "page_size": 20,
    })
    items = data.get("response", {}).get("items", [])
    shows = []
    for item in items:
        shows.append({
            "id": item.get("item_id"),
            "title": item.get("title"),
            "price": f"¥{int(item.get('price', 0)) / 100:.0f}",
            "stock": item.get("quantity"),
            "url": item.get("item_url") or f"https://h5.youzan.com/v2/goods/{item.get('alias')}",
        })
    if not shows:
        return "暂无在售演出，请关注后续场次。"
    result = "近期演出场次：\n\n"
    for s in shows:
        result += f"🎤 {s['title']}\n"
        result += f"   票价：{s['price']} | 余票：{s['stock']}\n"
        result += f"   购票：{s['url']}\n\n"
    return result.strip()


def get_show_detail(arguments: dict) -> str:
    """获取某场演出详情"""
    item_id = arguments.get("item_id")
    if not item_id:
        return "请提供演出ID"
    data = youzan_api("youzan.item.get", "3.0.0", {"item_id": item_id})
    item = data.get("response", {}).get("item", {})
    if not item:
        return "未找到该演出信息"
    alias = item.get("alias", "")
    return (
        f"🎤 {item.get('title')}\n"
        f"详情：{item.get('detail_url') or f'https://h5.youzan.com/v2/goods/{alias}'}\n"
        f"票价：¥{int(item.get('price', 0)) / 100:.0f}\n"
        f"余票：{item.get('quantity')}\n"
        f"购票链接：https://h5.youzan.com/v2/goods/{alias}"
    )


# ── MCP 协议处理 ────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_shows",
        "description": "获取脱口秀近期演出场次列表，包含票价和购票链接",
        "inputSchema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "get_show_detail",
        "description": "获取某场脱口秀演出的详细信息和购票链接",
        "inputSchema": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "演出商品ID，从get_shows结果中获取"
                }
            },
            "required": ["item_id"]
        }
    }
]

TOOL_HANDLERS = {
    "get_shows": get_shows,
    "get_show_detail": get_show_detail,
}


def handle_jsonrpc(body: dict) -> dict:
    method = body.get("method")
    req_id = body.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "standup-tickets", "version": "0.1.0"}
            }
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        tool_name = body.get("params", {}).get("name")
        arguments = body.get("params", {}).get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Tool not found"}}
        try:
            result = handler(arguments)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]}
            }
        except Exception as e:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(e)}}

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        response = handle_jsonrpc(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def do_GET(self):
        # 健康检查
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "standup-tickets-mcp"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

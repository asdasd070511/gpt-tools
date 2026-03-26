import os
import sys
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from curl_cffi import requests, CurlMime

MAX_WORKERS = 30
MAX_RETRIES = 3

CPA_API_URL = "http://180.214.181.219:8317/
CPA_API_TOKEN = "070587"  # CPA API Token（Bearer 认证）


def _normalize_cpa_url(api_url: str) -> str:
    """将 CPA 地址规范化为 auth-files 接口地址"""
    normalized = (api_url or "").strip().rstrip("/")
    lower = normalized.lower()
    if not normalized:
        return ""
    if lower.endswith("/auth-files"):
        return normalized
    if lower.endswith("/v0/management") or lower.endswith("/management"):
        return f"{normalized}/auth-files"
    if lower.endswith("/v0"):
        return f"{normalized}/management/auth-files"
    return f"{normalized}/v0/management/auth-files"


def push_to_cpa(token_json_str: str) -> bool:
    """将 token 推送到 CPA 服务器"""
    try:
        t = json.loads(token_json_str)
        email = t.get("email", "unknown")

        if not t.get("refresh_token"):
            print(f"[CPA] [{email}] 缺少 refresh_token，跳过推送")
            return False

        upload_url = _normalize_cpa_url(CPA_API_URL)
        if not upload_url or not CPA_API_TOKEN:
            print("[CPA] API URL 或 Token 未配置")
            return False

        filename = f"{email}.json"
        file_content = token_json_str.encode("utf-8")
        headers = {"Authorization": f"Bearer {CPA_API_TOKEN}"}

        # 尝试 multipart 上传
        mime = CurlMime()
        mime.addpart(
            name="file",
            data=file_content,
            filename=filename,
            content_type="application/json",
        )
        resp = requests.post(
            upload_url,
            multipart=mime,
            headers=headers,
            timeout=30,
            impersonate="chrome110",
        )

        if resp.status_code in (200, 201):
            print(f"[CPA] [{email}] 推送成功!")
            return True

        # multipart 失败，尝试 raw JSON 回退
        if resp.status_code in (404, 405, 415):
            raw_url = f"{upload_url}?name={quote(filename)}"
            resp = requests.post(
                raw_url,
                data=file_content,
                headers={**headers, "Content-Type": "application/json"},
                timeout=30,
                impersonate="chrome110",
            )
            if resp.status_code in (200, 201):
                print(f"[CPA] [{email}] 推送成功!")
                return True

        print(f"[CPA] [{email}] 推送失败 ({resp.status_code}): {resp.text[:200]}")
        return False

    except Exception as e:
        print(f"[CPA] 推送异常: {e}")
        return False


def main():
    tokens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")
    if not os.path.isdir(tokens_dir):
        print(f"[错误] tokens 目录不存在: {tokens_dir}")
        sys.exit(1)

    json_files = sorted(f for f in os.listdir(tokens_dir) if f.endswith(".json"))
    if not json_files:
        print("[提示] tokens 目录下没有 JSON 文件")
        sys.exit(0)

    print(f"[Info] 找到 {len(json_files)} 个 token 文件，使用 {MAX_WORKERS} 线程并发推送...\n")
    counter = {"success": 0, "fail": 0}
    counter_lock = threading.Lock()

    def process_file(fname):
        fpath = os.path.join(tokens_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"[错误] 读取 {fname} 失败: {e}")
            with counter_lock:
                counter["fail"] += 1
            return

        print(f"--- 处理: {fname}")
        ok = False
        for attempt in range(1, MAX_RETRIES + 1):
            if push_to_cpa(content):
                ok = True
                break
            if attempt < MAX_RETRIES:
                wait = attempt * 2
                print(f"[重试] {fname} 第 {attempt}/{MAX_RETRIES} 次失败，{wait}s 后重试...")
                time.sleep(wait)
        if not ok:
            print(f"[放弃] {fname} 已重试 {MAX_RETRIES} 次仍失败")
        with counter_lock:
            counter["success" if ok else "fail"] += 1

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(process_file, f): f for f in json_files}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                print(f"[错误] 线程异常 ({futures[fut]}): {e}")

    print(f"\n[完成] 成功: {counter['success']}, 失败: {counter['fail']}, 总计: {len(json_files)}")


if __name__ == "__main__":
    main()

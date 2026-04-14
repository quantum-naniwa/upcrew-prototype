#!/usr/bin/env python3
"""
常駐デーモン (daemon.py)

動作:
  - 起動時（ログイン時）に recorder.py を即時実行
  - スリープ復帰を検知して recorder.py を実行
    ※ 検知方法: sleep() のタイムギャップが想定の 2.5 倍以上なら復帰と判定
  - ローカル HTTP サーバー（port 8765）で再実行リンクを提供
    http://localhost:8765/rerun にアクセスすると rerun.py を起動

起動方法:
  setup_autostart.py を実行すると、このスクリプトが
  ログイン時に自動起動されるよう設定されます。
"""

import signal
import subprocess
import sys
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).parent
RECORDER = BASE_DIR / "recorder.py"
RERUN = BASE_DIR / "rerun.py"
PYTHON = sys.executable

CHECK_INTERVAL = 10  # 秒（スリープ復帰チェックの間隔）
HTTP_PORT = 8765


# ─── ログ ────────────────────────────────────────────────────────────────────


def log(msg: str) -> None:
    print(f"[daemon {datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ─── 録画起動 ─────────────────────────────────────────────────────────────────


def run_recorder() -> None:
    log("recorder.py を起動します")
    try:
        subprocess.Popen([PYTHON, str(RECORDER)])
    except Exception as e:
        log(f"recorder.py の起動に失敗しました: {e}")


def run_rerun() -> None:
    log("rerun.py を起動します（再実行リクエスト）")
    try:
        subprocess.Popen([PYTHON, str(RERUN)])
    except Exception as e:
        log(f"rerun.py の起動に失敗しました: {e}")


# ─── ローカル HTTP サーバー（再実行リンク用）──────────────────────────────────


class RerunHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/rerun":
            run_rerun()
            body = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>再実行</title>
  <style>
    body { font-family: sans-serif; display: flex; justify-content: center;
           align-items: center; height: 100vh; margin: 0; background: #f0f4f8; }
    .card { background: #fff; border-radius: 12px; padding: 40px;
            text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
    h1 { color: #2e7d32; }
    p  { color: #555; }
  </style>
</head>
<body>
  <div class="card">
    <h1>✅ 再実行を開始しました</h1>
    <p>録画スクリプトを起動しています。<br>しばらくお待ちください。</p>
  </div>
</body>
</html>"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # HTTPアクセスログを抑制


def start_http_server() -> None:
    try:
        server = HTTPServer(("localhost", HTTP_PORT), RerunHandler)
        log(f"再実行サーバー起動: http://localhost:{HTTP_PORT}/rerun")
        server.serve_forever()
    except Exception as e:
        log(f"HTTPサーバー起動失敗: {e}")


# ─── シグナルハンドラ ─────────────────────────────────────────────────────────


def handle_signal(sig, frame) -> None:
    log("終了シグナルを受信しました。デーモンを停止します。")
    sys.exit(0)


# ─── メイン ──────────────────────────────────────────────────────────────────


def main() -> None:
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # HTTPサーバーをバックグラウンドスレッドで起動
    threading.Thread(target=start_http_server, daemon=True).start()

    log("デーモン起動（ログイン検知）")
    run_recorder()  # ログイン時の即時実行

    last = time.time()
    while True:
        time.sleep(CHECK_INTERVAL)
        now = time.time()
        elapsed = now - last

        # スリープ復帰の検知: 実際の経過時間がチェック間隔の 2.5 倍以上
        if elapsed > CHECK_INTERVAL * 2.5:
            log(f"スリープ復帰を検知しました（{elapsed:.0f}秒のギャップ）")
            run_recorder()

        last = now


if __name__ == "__main__":
    main()

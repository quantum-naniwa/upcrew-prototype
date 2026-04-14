#!/usr/bin/env python3
"""
自動録画測定スクリプト (recorder.py)

動作:
  1. 本日分の録画が既に存在する場合はスキップして終了
  2. カメラアクセスを確認
  3. 30秒録画して保存
  4. 結果をログに記録
  5. 失敗時のみ Zapier Webhook へ通知
"""

import cv2
import json
import os
import sys
import time
import platform
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# ─── パス・設定 ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


config = load_config()

SYSTEM = platform.system()

if SYSTEM == "Darwin":
    SAVE_DIR = Path.home() / "Movies" / "recordings"
elif SYSTEM == "Windows":
    SAVE_DIR = Path.home() / "Videos" / "recordings"
else:
    SAVE_DIR = BASE_DIR / "recordings"

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "log.jsonl"

RECORD_DURATION: int = config.get("record_duration", 30)
ZAPIER_WEBHOOK_URL: str = config.get("zapier_webhook_url", "")

SAVE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ─── ログ ────────────────────────────────────────────────────────────────────


def log_result(success: bool, message: str, filepath: str = "") -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "message": message,
        "filepath": filepath,
        "platform": SYSTEM,
        "hostname": platform.node(),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    status = "SUCCESS" if success else "FAILURE"
    print(f"[{status}] {message}")


# ─── 本日分の録画チェック ─────────────────────────────────────────────────────


def today_recording_exists() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    return any(SAVE_DIR.glob(f"recording-{today}*.mp4"))


# ─── カメラ権限確認 (macOS) ───────────────────────────────────────────────────


def check_camera_permission_mac() -> tuple[bool, str]:
    """
    macOS の TCC でカメラ権限状態を確認。
    pyobjc なしで動作させるため、avfoundation を subprocess で呼ぶ。
    権限がない場合はダイアログを出す（ユーザー操作が必要）。
    """
    try:
        result = subprocess.run(
            [
                "python3", "-c",
                (
                    "import objc, AVFoundation\n"
                    "status = AVFoundation.AVCaptureDevice"
                    ".authorizationStatusForMediaType_('vide')\n"
                    "print(status)"
                ),
            ],
            capture_output=True, text=True, timeout=5
        )
        status_code = result.stdout.strip()
        # 3 = authorized, 0 = notDetermined, 1 = restricted, 2 = denied
        if status_code == "2":
            return False, "カメラへのアクセスが拒否されています。システム環境設定 > プライバシー > カメラ で許可してください。"
        if status_code == "1":
            return False, "カメラへのアクセスが制限されています。"
        return True, "OK"
    except Exception:
        # pyobjc が使えない環境では OpenCV の open() 結果で判断
        return True, "OK (権限確認スキップ)"


# ─── 録画 ────────────────────────────────────────────────────────────────────


def record_video() -> tuple[bool, str, str]:
    """
    カメラから RECORD_DURATION 秒録画して MP4 ファイルに保存。
    Returns: (success, message, filepath)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = str(SAVE_DIR / f"recording-{timestamp}.mp4")

    # macOS: カメラ権限を事前確認
    if SYSTEM == "Darwin":
        ok, reason = check_camera_permission_mac()
        if not ok:
            return False, reason, ""

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return (
            False,
            "カメラを起動できませんでした（権限がないか、他のアプリが使用中の可能性があります）",
            "",
        )

    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

        if not out.isOpened():
            cap.release()
            return False, "動画ファイルを作成できませんでした（書き込み権限を確認してください）", ""

        print(f"[INFO] 録画開始 ({RECORD_DURATION}秒): {filepath}")
        start = time.time()
        frames_written = 0

        while time.time() - start < RECORD_DURATION:
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frames_written += 1

    except Exception as e:
        return False, f"録画中に例外が発生しました: {e}", ""
    finally:
        cap.release()
        try:
            out.release()
        except Exception:
            pass

    if frames_written == 0:
        return False, "フレームを1枚も取得できませんでした（カメラ映像が取得できていません）", ""

    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    return (
        True,
        f"録画完了: {frames_written}フレーム / {file_size:,}バイト",
        filepath,
    )


# ─── Zapier Webhook 通知 ──────────────────────────────────────────────────────


def notify_zapier(error_message: str) -> None:
    if not ZAPIER_WEBHOOK_URL or ZAPIER_WEBHOOK_URL.startswith("https://hooks.zapier.com/hooks/catch/YOUR"):
        print("[WARN] config.json の zapier_webhook_url が未設定です。通知をスキップします。")
        return

    payload = {
        "event": "recording_failed",
        "timestamp": datetime.now().isoformat(),
        "hostname": platform.node(),
        "platform": SYSTEM,
        "error": error_message,
        "rerun_url": "http://localhost:8765/rerun",
    }
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.post(ZAPIER_WEBHOOK_URL, json=payload, timeout=10, verify=False)
        print(f"[INFO] Zapier 通知送信完了 (HTTP {resp.status_code})")
    except requests.RequestException as e:
        print(f"[ERROR] Zapier 通知失敗: {e}")


# ─── メイン ──────────────────────────────────────────────────────────────────


def main() -> None:
    print(f"[INFO] recorder.py 起動: {datetime.now().isoformat()}")

    # 本日分がすでに存在する場合はスキップ
    if today_recording_exists():
        print("[INFO] 本日分の録画が既に存在します。スキップして終了します。")
        sys.exit(0)

    success, message, filepath = record_video()
    log_result(success, message, filepath)

    if not success:
        notify_zapier(message)
        sys.exit(1)


if __name__ == "__main__":
    main()

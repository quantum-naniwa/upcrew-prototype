#!/usr/bin/env python3
"""
強制再実行スクリプト (rerun.py)

Slack の通知リンクや手動実行から呼ばれ、
本日分の録画を削除してから recorder.py を実行します。

使い方:
  python3 rerun.py

Slack からのディープリンク例 (config.json の slack_rerun_url に設定):
  - カスタムスキーマ + AppleScript, ショートカット, etc. で呼び出す
  - または、共有フォルダの HTML ファイルからワンクリック実行する形も可
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
import json
import platform

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
RECORDER = BASE_DIR / "recorder.py"
PYTHON = sys.executable

SYSTEM = platform.system()

if SYSTEM == "Darwin":
    SAVE_DIR = Path.home() / "Movies" / "recordings"
elif SYSTEM == "Windows":
    SAVE_DIR = Path.home() / "Videos" / "recordings"
else:
    SAVE_DIR = BASE_DIR / "recordings"


def remove_today_recordings() -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    removed = 0
    for f in SAVE_DIR.glob(f"recording-{today}*.mp4"):
        f.unlink()
        print(f"[INFO] 削除: {f}")
        removed += 1
    return removed


def main() -> None:
    print(f"[INFO] rerun.py 起動: {datetime.now().isoformat()}")

    removed = remove_today_recordings()
    if removed > 0:
        print(f"[INFO] 本日分の録画 {removed} 件を削除しました。")
    else:
        print("[INFO] 削除する本日分の録画はありませんでした。")

    print("[INFO] recorder.py を起動します...")
    result = subprocess.run([PYTHON, str(RECORDER)])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

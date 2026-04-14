#!/usr/bin/env python3
"""
自動起動設定スクリプト (setup_autostart.py)

このスクリプトを一度実行するだけで、OS ログイン時に daemon.py が
自動起動されるよう設定されます。

  Mac  : ~/Library/LaunchAgents/com.autostart.recorder.plist を生成し launchctl でロード
  Win  : schtasks でログオン時＆スリープ復帰トリガーのタスクを登録
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

SYSTEM = platform.system()
BASE_DIR = Path(__file__).parent.resolve()
DAEMON = BASE_DIR / "daemon.py"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LABEL = "com.autostart.recorder"
PYTHON = sys.executable


# ─── Mac (LaunchAgent) ───────────────────────────────────────────────────────


def setup_mac() -> None:
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents_dir / f"{LABEL}.plist"

    stdout_log = LOG_DIR / "daemon.log"
    stderr_log = LOG_DIR / "daemon_error.log"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON}</string>
        <string>{DAEMON}</string>
    </array>

    <!-- ログイン時に自動起動 -->
    <key>RunAtLoad</key>
    <true/>

    <!-- クラッシュ時に自動再起動 -->
    <key>KeepAlive</key>
    <true/>

    <!-- 標準出力・エラーをログファイルへ -->
    <key>StandardOutPath</key>
    <string>{stdout_log}</string>
    <key>StandardErrorPath</key>
    <string>{stderr_log}</string>
</dict>
</plist>
"""

    plist_path.write_text(plist_content, encoding="utf-8")
    print(f"[INFO] plist を作成しました: {plist_path}")

    # すでにロードされている場合はアンロードしてから再ロード
    subprocess.run(
        ["launchctl", "unload", str(plist_path)],
        capture_output=True
    )
    result = subprocess.run(
        ["launchctl", "load", str(plist_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[SUCCESS] LaunchAgent を登録しました。次回ログイン時から自動起動されます。")
        print(f"          今すぐ起動したい場合: launchctl start {LABEL}")
    else:
        print(f"[ERROR] LaunchAgent の登録に失敗しました: {result.stderr}")
        sys.exit(1)


def unload_mac() -> None:
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    if not plist_path.exists():
        print("[INFO] 登録された LaunchAgent が見つかりません。")
        return
    subprocess.run(["launchctl", "unload", str(plist_path)])
    plist_path.unlink()
    print(f"[SUCCESS] LaunchAgent を削除しました: {plist_path}")


# ─── Windows (Task Scheduler) ────────────────────────────────────────────────


def setup_windows() -> None:
    task_name = "AutostartRecorder"
    # ログオントリガー
    cmd_logon = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", f'"{PYTHON}" "{DAEMON}"',
        "/sc", "ONLOGON",
        "/rl", "HIGHEST",
        "/f",  # 上書き
    ]
    result = subprocess.run(cmd_logon, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] タスク登録失敗 (ONLOGON): {result.stderr}")
        sys.exit(1)

    print(f"[SUCCESS] タスクスケジューラに '{task_name}' を登録しました（ログオン時トリガー）。")
    print("          スリープ復帰後の再実行は daemon.py 内で自動検知されます。")


def unload_windows() -> None:
    task_name = "AutostartRecorder"
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[SUCCESS] タスク '{task_name}' を削除しました。")
    else:
        print(f"[ERROR] タスク削除失敗: {result.stderr}")


# ─── メイン ──────────────────────────────────────────────────────────────────


def main() -> None:
    action = "setup"
    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        action = "uninstall"

    if SYSTEM == "Darwin":
        if action == "setup":
            setup_mac()
        else:
            unload_mac()
    elif SYSTEM == "Windows":
        if action == "setup":
            setup_windows()
        else:
            unload_windows()
    else:
        print(f"[ERROR] 未対応のOS: {SYSTEM}")
        sys.exit(1)


if __name__ == "__main__":
    main()

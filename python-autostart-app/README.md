# python-autostart-app

ログイン時・スリープ復帰時にカメラ録画を自動実行する試作アプリです。
録画に失敗した場合は Zapier 経由で Slack に通知します。

---

## システム構成

```
ログイン / スリープ復帰
        ↓
   daemon.py（常駐）
   ├── HTTPサーバー起動（port 8765）
   └── recorder.py を起動
        ↓
   recorder.py（30秒録画）
    ├── 本日分が既にある → スキップ終了
    ├── 成功 → ~/Movies/recordings/ に保存 + logs/log.jsonl に記録
    └── 失敗 → Zapier Webhook → Slack通知（再実行リンク付き）
                                        ↓
                              http://localhost:8765/rerun をクリック
                                        ↓
                                rerun.py（本日分削除 → 再録画）
```

---

## 動作環境

| 項目 | 要件 |
|------|------|
| OS | macOS / Windows |
| Python | 3.9 以上 |
| カメラ | 内蔵または外付けカメラ |
| ネットワーク | 失敗通知時にインターネット接続が必要 |

---

## セットアップ手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/quantum-naniwa/upcrew-prototype.git
cd upcrew-prototype
git checkout feature/python-autostart
cd python-autostart-app
```

### 2. 依存パッケージをインストール

**Mac:**
```bash
pip3 install -r requirements.txt --break-system-packages
```

**Windows:**
```bash
pip install -r requirements.txt
```

### 3. 設定ファイルを作成

```bash
cp config.example.json config.json
```

次に `config.json` を開いて Zapier の Webhook URL を設定します。以下のいずれかの方法で開いてください：

**方法① Finder / テキストエディットで開く（推奨）**
```bash
open python-autostart-app/config.json
```

**方法② ターミナル内で編集（nano）**
```bash
nano python-autostart-app/config.json
# 編集後: Ctrl+O で保存 → Ctrl+X で終了
```

**方法③ VS Code で開く**
```bash
code python-autostart-app/config.json
```

開いたら `zapier_webhook_url` の値を SE 担当者から受け取った URL に書き換えて保存してください：

```json
{
  "zapier_webhook_url": "https://hooks.zapier.com/hooks/catch/XXXXX/YYYYY/",
  "record_duration": 30,
  "slack_rerun_url": "http://localhost:8765/rerun"
}
```

### 4. 自動起動を登録

```bash
python3 setup_autostart.py
```

以下が表示されれば完了です：

```
[SUCCESS] LaunchAgent を登録しました。次回ログイン時から自動起動されます。
```

**次回ログイン時から自動録画が始まります。**

---

## テスト手順

セットアップ後、以下の順番で動作を確認してください。

---

### STEP 1 — 自動起動の登録確認

LaunchAgent が正しく登録されているか確認します：

```bash
launchctl list | grep com.autostart.recorder
```

以下のように PID が表示されれば登録済みです：

```
12345   0   com.autostart.recorder
```

plist ファイルの存在も確認できます：

```bash
cat ~/Library/LaunchAgents/com.autostart.recorder.plist
```

---

### STEP 2 — ログイン時の自動起動確認

実際にログアウト → ログインして自動起動を確認します：

1. ターミナルで以下を実行してデーモンを停止
```bash
launchctl stop com.autostart.recorder
```

2. Mac をログアウト（Apple メニュー → ログアウト）

3. ログイン後、ターミナルを開いてログを確認
```bash
tail -20 logs/daemon.log
```

ログイン直後に録画が自動実行されていれば成功です：

```
[daemon HH:MM:SS] デーモン起動（ログイン検知）
[daemon HH:MM:SS] recorder.py を起動します
[SUCCESS] 録画完了: 900フレーム / XX,XXXバイト
```

---

### STEP 3 — スリープ復帰の自動起動確認

スリープからの復帰は以下の2パターンどちらも自動で動作します：

| パターン | 動作 |
|---------|------|
| スリープ → 復帰（画面ロックなし） | daemon.py が時間ギャップを検知して録画 |
| スリープ → 復帰 → ログイン（画面ロック解除） | daemon.py は KeepAlive で常駐しているため、画面ロック解除前に復帰を検知して録画 |

**テスト手順：**

1. 本日分の録画を削除（スキップされないよう）
```bash
python3 rerun.py
```

2. Mac をスリープ（Apple メニュー → スリープ）

3. スリープ復帰後（画面ロックがある場合はログイン）、ログを確認
```bash
tail -10 logs/daemon.log
```

以下が表示されれば復帰検知が動作しています：

```
[daemon HH:MM:SS] スリープ復帰を検知しました（XX秒のギャップ）
[daemon HH:MM:SS] recorder.py を起動します
[SUCCESS] 録画完了: 900フレーム / XX,XXXバイト
```

---

### STEP 4 — デーモンを手動起動

```bash
launchctl start com.autostart.recorder
```

### STEP 5 — デーモンの起動確認

```bash
tail -f logs/daemon.log
```

以下が表示されれば正常です：

```
[daemon HH:MM:SS] 再実行サーバー起動: http://localhost:8765/rerun
[daemon HH:MM:SS] デーモン起動（ログイン検知）
[daemon HH:MM:SS] recorder.py を起動します
[INFO] recorder.py 起動: YYYY-MM-DDTHH:MM:SS
[INFO] 録画開始 (30秒): ~/Movies/recordings/recording-YYYY-MM-DD_HH-MM-SS.mp4
[SUCCESS] 録画完了: XXXXフレーム / XX,XXXバイト
```

`Ctrl+C` でログ監視を終了します。

---

### STEP 6 — 成功パスのテスト（録画 → 保存）

本日分の録画を削除して再録画します：

```bash
python3 rerun.py
```

以下が表示されれば成功です：

```
[INFO] 本日分の録画 1 件を削除しました。
[INFO] recorder.py を起動します...
[SUCCESS] 録画完了: 900フレーム / XX,XXXバイト
```

録画ファイルの確認：

```bash
open ~/Movies/recordings/
```

---

### STEP 7 — 失敗パスのテスト（Zapier → Slack通知）

録画失敗を意図的に発生させて Slack 通知を確認します：

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
import recorder
recorder.notify_zapier('カメラを起動できませんでした（テスト）')
print('通知送信完了')
"
```

Slack の通知チャンネルに以下のようなメッセージが届きます：

```
⚠️ 録画失敗アラート

PC名: your-mac
日時: YYYY-MM-DDTHH:MM:SS
エラー: カメラを起動できませんでした（テスト）

▶️ 再実行はこちら（ご自身のPCのブラウザで開いてください）
http://localhost:8765/rerun
```

---

### STEP 8 — 再実行リンクのテスト

STEP 7 で届いた Slack 通知の `http://localhost:8765/rerun` を  
**ご自身の PC のブラウザで開いてください。**

ブラウザに「✅ 再実行を開始しました」と表示されれば成功です。

ログで確認：

```bash
tail -5 logs/daemon.log
```

```
[daemon HH:MM:SS] rerun.py を起動します（再実行リクエスト）
```

---

### STEP 9 — ログの確認

```bash
cat logs/log.jsonl
```

録画結果が JSON 形式で記録されています：

```json
{"timestamp": "2026-04-14T14:52:00", "success": true, "message": "録画完了: 900フレーム", "filepath": "~/Movies/recordings/recording-2026-04-14_14-52-00.mp4", "platform": "Darwin", "hostname": "your-mac"}
```

---

## ファイル構成

| ファイル | 説明 |
|---------|------|
| `recorder.py` | カメラ録画・エラー処理・Zapier通知 |
| `daemon.py` | 常駐プロセス（ログイン検知・スリープ復帰検知・再実行HTTPサーバー） |
| `setup_autostart.py` | 自動起動の登録・解除 |
| `rerun.py` | 強制再実行（本日分削除→再録画） |
| `config.json` | 設定ファイル（各端末で個別に作成・gitignore対象） |
| `config.example.json` | 設定ファイルのテンプレート |
| `logs/log.jsonl` | 録画実行結果ログ |
| `logs/daemon.log` | デーモン動作ログ |

---

## 録画ファイルの保存先

| OS | 保存先 |
|----|--------|
| Mac | `~/Movies/recordings/` |
| Windows | `~/Videos/recordings/` |

ファイル名: `recording-YYYY-MM-DD_HH-MM-SS.mp4`

Finder から開く：

```bash
open ~/Movies/recordings/
```

---

## 自動起動を解除したい場合

```bash
python3 setup_autostart.py uninstall
```

---

## トラブルシューティング

| 症状 | 対処 |
|------|------|
| カメラが起動しない | システム環境設定 > プライバシー > カメラ で Python を許可 |
| Slack 通知が届かない | `config.json` の `zapier_webhook_url` を確認 |
| 録画がスキップされる | 本日分が既に存在（正常動作）。再実行は `python3 rerun.py` |
| 再実行リンクが開かない | `launchctl start com.autostart.recorder` でデーモンを起動 |
| SSL エラーが出る | 社内ネットワークのプロキシが原因。SE に確認 |

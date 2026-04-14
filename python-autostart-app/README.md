# python-autostart-app

ログイン時・スリープ復帰時にカメラ録画を自動実行する試作アプリです。
録画に失敗した場合は Zapier 経由で Slack に通知します。

---

## システム構成

```
ログイン / スリープ復帰
        ↓
   daemon.py（常駐）
        ↓
   recorder.py（録画）
    ├── 成功 → ~/Movies/recordings/ に保存 + ログ記録
    └── 失敗 → Zapier Webhook → Slack 通知
                                    ↓
                          再実行リンクをクリック
                                    ↓
                            rerun.py（再実行）
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

`config.json` を開き、Zapier の Webhook URL を設定してください：

```json
{
  "zapier_webhook_url": "https://hooks.zapier.com/hooks/catch/XXXXX/YYYYY/",
  "record_duration": 30,
  "slack_rerun_url": "http://localhost:8765/rerun"
}
```

> `zapier_webhook_url` は SE 担当者に確認してください。

### 4. 自動起動を登録

```bash
python3 setup_autostart.py
```

成功すると以下が表示されます：

```
[SUCCESS] LaunchAgent を登録しました。次回ログイン時から自動起動されます。
```

**これで設定完了です。次回ログイン時から自動録画が始まります。**

---

## 動作確認（任意）

セットアップ後、手動でテストする場合：

```bash
# 録画テスト（30秒録画して保存）
python3 recorder.py

# 強制再実行（本日分を削除して再録画）
python3 rerun.py
```

---

## ファイル構成

| ファイル | 説明 |
|---------|------|
| `recorder.py` | カメラ録画・エラー処理・Slack通知 |
| `daemon.py` | 常駐プロセス（ログイン検知・スリープ復帰検知・再実行サーバー） |
| `setup_autostart.py` | 自動起動の登録・解除 |
| `rerun.py` | 強制再実行 |
| `config.json` | 設定ファイル（各端末で個別に作成） |
| `config.example.json` | 設定ファイルのテンプレート |

---

## 録画ファイルの保存先

| OS | 保存先 |
|----|--------|
| Mac | `~/Movies/recordings/` |
| Windows | `~/Videos/recordings/` |

ファイル名: `recording-YYYY-MM-DD_HH-MM-SS.mp4`

---

## ログの確認

```bash
# 実行結果ログ
cat logs/log.jsonl

# デーモンログ
cat logs/daemon.log
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
| 録画がスキップされる | 本日分が既に存在します（正常動作） |
| 再実行したい | `python3 rerun.py` を実行 |

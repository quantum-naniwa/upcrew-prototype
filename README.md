# upcrew-prototype

ログイン時・スリープ復帰時にカメラ録画を自動実行する試作プロジェクトです。

---

## アプリ一覧

| アプリ | ブランチ | 説明 |
|--------|---------|------|
| [python-autostart-app](./python-autostart-app/) | `feature/python-autostart` | Python製。カメラ自動録画・失敗時Slack通知 |
| [electron-autostart-app](./electron-autostart-app/) | `feature/electron-autostart` | Electron製。タスク管理UI・カメラ録画 |

---

## セットアップ（python-autostart-app）

```bash
git clone https://github.com/quantum-naniwa/upcrew-prototype.git
cd upcrew-prototype
git checkout feature/python-autostart
cd python-autostart-app
pip3 install -r requirements.txt --break-system-packages
cp config.example.json config.json
# config.json に Zapier Webhook URL を設定
python3 setup_autostart.py
```

詳細は [python-autostart-app/README.md](./python-autostart-app/README.md) を参照してください。

---

## システム構成

```
ログイン / スリープ復帰
        ↓
   daemon.py（常駐）
        ↓
   recorder.py（30秒録画）
    ├── 成功 → ローカルに保存
    └── 失敗 → Zapier → Slack通知 → 再実行リンク
```

# perfectcorp-mcp

Perfect Corp AI APIs を Claude Code から呼び出すための MCP サーバです。

現在対応している分析:
- **Skin Analysis** — 肌状態の分析

将来追加予定:
- Face Analysis
- Hair Analysis

## アーキテクチャ

```
Claude Code
    │  MCP (stdio)
    ▼
server.py                  ← FastMCP ツール定義・入力バリデーション
    │
    ▼
perfectcorp/apis/skin_v21.py  ← v2.1 ワークフロー (dst_actions 管理)
    │
    ▼
perfectcorp/client.py      ← HTTP クライアント (認証・アップロード・ポーリング)
    │
    ├─ POST /s2s/v2.1/file/skin-analysis  → presigned URL + file_id
    ├─ PUT  {presigned_url}               → ファイルアップロード
    ├─ POST /s2s/v2.1/task/skin-analysis  → task_id
    └─ GET  /s2s/v2.1/task/skin-analysis/{task_id}  → 結果 (ポーリング)
```

| レイヤー | ファイル | 責務 |
|---|---|---|
| MCP ツール | `server.py` | ツール定義・入力バリデーション・JSON シリアライズ |
| API モジュール | `perfectcorp/apis/skin_v21.py` | v2.1 フロー・dst_actions バリデーション |
| HTTP クライアント | `perfectcorp/client.py` | 認証・2段階アップロード・非同期ポーリング |

新しい API を追加する場合は `perfectcorp/apis/` にモジュールを追加し、`server.py` に `@mcp.tool()` を追記するだけです。

---

## セットアップ

### 1. リポジトリをクローン / 移動

```bash
cd /path/to/perfectcorp-mcp
```

### 2. Python 3.10 以上の仮想環境を作成して依存パッケージをインストール

```bash
python3.11 -m venv .venv
.venv/bin/pip install "mcp[cli]" "httpx" "python-dotenv"
```

> Python 3.10 未満（macOS デフォルトの 3.9 等）では `mcp` がインストールできません。
> pyenv / Homebrew で 3.10 以上のバージョンを用意してください。

### 3. `.env` ファイルを作成

```bash
cp .env.example .env
```

`.env` を開き、API キーを設定してください:

```env
PERFECTCORP_API_KEY=your_api_key_here
```

API キーは [YouCam API Console](https://yce.makeupar.com/api-console/en/api-keys/) で取得できます。

---

## Claude Code への MCP 登録

### 方法 A: `claude mcp add` コマンド（推奨）

```bash
claude mcp add perfectcorp-ai \
  /絶対パス/perfectcorp-mcp/.venv/bin/python3 \
  /絶対パス/perfectcorp-mcp/server.py
```

例（このリポジトリを `/Users/naosuke/Repos/perfectcorp-mcp` に置いた場合）:

```bash
claude mcp add perfectcorp-ai \
  /Users/naosuke/Repos/perfectcorp-mcp/.venv/bin/python3 \
  /Users/naosuke/Repos/perfectcorp-mcp/server.py
```

### 方法 B: `settings.json` に手動追加

`~/.claude/settings.json` を開き、`mcpServers` に以下を追加:

```json
{
  "mcpServers": {
    "perfectcorp-ai": {
      "command": "/Users/naosuke/Repos/perfectcorp-mcp/.venv/bin/python3",
      "args": ["/Users/naosuke/Repos/perfectcorp-mcp/server.py"]
    }
  }
}
```

登録後は Claude Code を再起動（または `/mcp` でサーバー一覧を確認）してください。

---

## 使い方

Claude Code のチャットで以下のように依頼します:

```
この画像の肌を分析してください: /path/to/face.jpg
```

Claude が `analyze_skin_image` ツールを呼び出し、API レスポンスを受け取って解釈・要約します。

---

## ツール仕様

### `analyze_skin_image(image_path: str) -> str`

| 項目 | 詳細 |
|------|------|
| 入力 | `image_path` — ローカル画像ファイルの絶対パス（`~` 展開可） |
| 対応形式 | jpg / jpeg / png |
| ファイルサイズ制限 | 最大 10 MB |
| 画像サイズ制限 | 長辺 4096 px 以内 |
| 戻り値 | Perfect Corp API のレスポンス JSON（加工なし） |

---

## 処理フロー

```
1. 画像ファイルを File API にアップロード → file_id を取得
2. POST /s2s/v2.0/task/skin-analysis で分析タスクを作成 → task_id を取得
3. GET /s2s/v2.0/task/skin-analysis/{task_id} を定期ポーリング
4. task_status = "success" になったらレスポンスを返却
```

---

## 新しい分析 API を追加する方法

`perfectcorp/apis/` に新しいファイルを作成します:

```python
# perfectcorp/apis/face.py
from perfectcorp.client import PerfectCorpClient

TASK_ENDPOINT = "/s2s/v2.0/task/face-analysis"

async def analyze_face(client: PerfectCorpClient, image_path: str) -> dict:
    file_id = await client.upload_file(image_path)
    task_id = await client.create_task(TASK_ENDPOINT, {"file_id": file_id})
    return await client.poll_task(TASK_ENDPOINT, task_id)
```

次に `server.py` に MCP ツールを追加します:

```python
from perfectcorp.apis.face import analyze_face

@mcp.tool()
async def analyze_face_image(image_path: str) -> str:
    """Analyze facial features using Perfect Corp Face Analysis API."""
    # ... バリデーション ...
    client = PerfectCorpClient()
    result = await analyze_face(client, str(path))
    return json.dumps(result, ensure_ascii=False, indent=2)
```

---

## 参考リンク

- [Perfect Corp API ドキュメント](https://docs.perfectcorp.com/reference/ai_skin_analysis)
- [Quick Start Guide](https://docs.perfectcorp.com/develop/quick_start_guide)
- [エラーコード一覧](https://docs.perfectcorp.com/develop/error_codes)
- [API Console (API キー発行)](https://yce.makeupar.com/api-console/)

# Zenn 記事ノート: Perfect Corp AI × Claude Code MCP サーバ構築

## 記事コンセプト

「Perfect Corp の AI Skin Analysis API を Claude Code から使えるようにする MCP サーバを Python で作った」

顔写真を渡すと肌状態を分析してくれる API を、Claude Code のツールとして呼び出せるようにする。
分析結果の解釈・要約は Claude 側に任せ、MCP サーバは API の橋渡しに徹するシンプルな設計。

---

## やったこと（時系列）

### 1. API ドキュメント調査

- Perfect Corp の docs サイト（docs.perfectcorp.com）は **JavaScript レンダリングの SPA** のため、WebFetch では本文を取得できなかった
- ナビゲーション構造とページ URL パターンから各エンドポイントの URL を特定
- `.md` 拡張子付き URL（例: `.../post.md`）にアクセスしたら API 仕様を取得できた

取得できた情報:
- ベース URL: `https://yce-api-01.perfectcorp.com`
- 認証: `Authorization: Bearer {API_KEY}`
- v2.1 の3エンドポイント仕様（後述）

### 2. v2.0 と v2.1 の違い

| 項目 | v2.0 | v2.1 |
|---|---|---|
| ファイルアップロード | multipart POST 1ステップ | presigned URL 2ステップ |
| アップロード先 | `/s2s/v2.0/file` | `/s2s/v2.1/file/skin-analysis`（機能別） |
| 分析項目指定 | なし | `dst_actions`（HD 16種 / SD 16種） |
| HD/SD 混在 | — | エラー（どちらか一方のみ） |
| ポーリング間隔 | 固定 | レスポンスの `polling_interval` を参照 |
| エラーフィールド | `error_code` | `error` + `error_message` |
| 最大解像度 | 1920px | 4096px |

### 3. v2.1 ファイルアップロードのフロー（ハマりポイント）

単純な multipart ではなく **2ステップ**:

```
Step 1: POST /s2s/v2.1/file/skin-analysis
  Body: { files: [{ content_type, file_name, file_size }] }
  Response: { files: [{ file_id, requests: [{ method, url, headers }] }] }

Step 2: PUT {presigned_url}
  Headers: Content-Type, Content-Length（レスポンスの headers をそのまま使う）
  Body: 画像バイナリ
  ※ Authorization ヘッダは不要（presigned URL に認証情報が埋め込まれている）
```

### 4. プロジェクト構成

```
perfectcorp-mcp/
├── server.py                      # MCP ツール定義・バリデーション
├── perfectcorp/
│   ├── client.py                  # HTTP クライアント（認証・アップロード・ポーリング）
│   └── apis/
│       ├── skin_v21.py            # Skin Analysis v2.1
│       ├── skin.py                # v2.0（参考用）
│       ├── face.py                # スタブ（将来用）
│       └── hair.py                # スタブ（将来用）
├── tests/
│   ├── test_server.py             # バリデーション・ハッピーパステスト
│   └── test_skin_v21.py           # dst_actions バリデーションテスト
├── .claude/settings.json          # このリポジトリ用 MCP 登録
└── .env                           # API キー（git 管理外）
```

### 5. MCP ツールの設計

```python
@mcp.tool()
async def analyze_skin_image(
    image_path: str,
    dst_actions: list[str] | None = None,  # デフォルト: HD 全16種
    format: str = "json",                  # "json" or "zip"
) -> str:
    ...
```

- `dst_actions` を省略すると HD 全16種が使われる
- `format="json"` にするとレスポンスに結果が直接入る（Claude が解釈しやすい）
- `format="zip"` だとダウンロード URL が返ってくる

### 6. Claude Code への MCP 登録方法

**プロジェクトローカル**（`.claude/settings.json` を置くだけ）:
```json
{
  "mcpServers": {
    "perfectcorp-ai": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/server.py"],
      "env": { "PYTHONPATH": "/path/to/perfectcorp-mcp" }
    }
  }
}
```
→ そのディレクトリで `claude` を起動すると自動で読み込まれる

**グローバル登録**（どこからでも使いたい場合）:
```bash
claude mcp add perfectcorp-ai \
  /path/to/.venv/bin/python3 \
  /path/to/server.py
```

### 7. テスト戦略

API を呼ばずに検証できるテストを先に書く:

- ファイルバリデーション（不存在・非対応拡張子・サイズ超過・不正 format）
- dst_actions バリデーション（HD/SD 混在・不明な値）
- ハッピーパス: `analyze_skin_v21` をモックして JSON が返ることを確認

```bash
PYTHONPATH=. .venv/bin/python3 -m pytest tests/ -v
# 18 passed
```

### 8. 環境構築でハマった点

- macOS デフォルトの Python は **3.9** → `mcp` パッケージは **3.10 以上**が必要
- pyenv で 3.11 をインストール済みだったので、そちらで venv を作成:
  ```bash
  ~/.pyenv/versions/3.11.8/bin/python3.11 -m venv .venv
  ```

---

## 使い方（記事のデモ用）

```
# Claude Code を起動（このリポジトリ内）
cd /path/to/perfectcorp-mcp
claude

# Claude Code 内で
「この画像の肌を分析して: ~/Desktop/face.jpg」
```

Claude が自動で `analyze_skin_image` ツールを呼び出し、API レスポンスを受け取って解釈・要約してくれる。

---

## 記事に入れたいポイント（ネタ候補）

- MCP サーバは「APIの薄いラッパー」として作るのが Claude との相性がいい（解釈は Claude に任せる）
- Perfect Corp には公式 MCP サーバ（`mcp-api-01.makeupar.com/mcp`）が既に存在するが、自前で作ると dst_actions の制御や将来の拡張が自由
- `.claude/settings.json` をリポジトリに置くだけで MCP がチーム共有できる
- SPA ドキュメントは WebFetch で取れないことがある → `.md` URL パターンを試すと取れることがある

---

## 参考リンク

- [Perfect Corp API Docs](https://docs.perfectcorp.com/reference/ai_skin_analysis)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP ドキュメント](https://gofastmcp.com/)
- [今回作ったリポジトリ](https://github.com/optimisuke/perfectcorp-mcp)

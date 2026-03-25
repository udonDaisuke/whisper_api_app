# DevOps/インフラエンジニア視点の分析

## 1. インフラ構成

### 推奨: セルフホスト (自宅GPU PC + Cloudflare Tunnel)

| 構成 | 月額コスト |
|------|-----------|
| **セルフホスト** | ~3,000円 (電気代のみ) |
| クラウド最安 (Vast.ai) | ~7,500円 |
| クラウド推奨 (GCP L4) | ~55,000円 |

- RTX 3060 (12GB) でWhisper small/mediumの推論は十分
- Cloudflare Tunnel で無料HTTPS公開（ポート開放不要）

## 2. Docker構成

### docker-compose.yml (開発用)

```yaml
services:
  api:       # FastAPI + Whisper
  db:        # PostgreSQL 16
  redis:     # Redis 7
```

### GPU対応: docker-compose.gpu.yml (オーバーレイ)

```bash
# CPU開発
docker compose up -d

# GPU開発
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### マルチステージ Dockerfile

- Stage 1: ビルド (gcc, pip install)
- Stage 2: ランタイム (slim, 非rootユーザー, HEALTHCHECK付き)

## 3. GPU環境

### ホスト必須セットアップ

1. NVIDIA ドライバ (nvidia-driver-550)
2. NVIDIA Container Toolkit
3. 動作確認 (`docker run --rm --gpus all nvidia/smi`)

### requirements分離

- `requirements-cpu.txt` — CPU版PyTorch
- `requirements-gpu.txt` — CUDA版PyTorch

## 4. CI/CD (GitHub Actions)

```
PR作成 → lint (ruff) + test (pytest) → レビュー → mainマージ
                                                    → イメージビルド (GHCR)
                                                    → SSH経由デプロイ
```

- GPU必要なテストは self-hosted runner or 手動テスト
- Docker イメージは GHCR にプッシュ

## 5. ストレージ

### 音声ファイル

```
/data/audio/raw/{user_id}/{YYYY-MM}/{uuid}.wav     # 元音声 (30日保持)
/data/audio/processed/{uuid}.wav                     # 前処理済み (完了後削除)
/data/audio/tmp/                                     # 一時ファイル (1時間で自動削除)
```

### モデルファイル

- Docker named volume で永続化
- 本番イメージにモデルを焼き込むオプション

## 6. 監視・ログ

### 構造化ログ (print → structlog)

JSON形式の構造化ログに置換。

### 軽量監視スタック

| 段階 | ツール |
|------|--------|
| 最初 | Docker ログ + `docker stats` |
| 次 | **Dozzle** (DockerログWebUI) |
| 成長時 | Prometheus + Grafana |
| 外部 | UptimeRobot (無料) |

### ヘルスチェック拡張

```python
GET /v1/health → {
  "status": "healthy",
  "checks": {
    "api": "ok",
    "model_loaded": true,
    "gpu_available": true,
    "disk_free_gb": 42.5
  }
}
```

## 7. セキュリティ

- **HTTPS**: Cloudflare Tunnel (無料、ポート開放不要、DDoS防御付き)
- **認証**: API Key認証 → JWT (マルチユーザー時)
- **音声データ**: 一時ファイル即削除、本番でのログ出力無効化
- **WebSocket**: 初回メッセージでトークン検証

## 8. 開発フロー

```
main (本番) ← PR マージで自動デプロイ
  └── feature/xxx ← 作業ブランチ
```

個人開発では main + feature の2層で十分。

### 環境別設定

```python
class Settings(BaseSettings):
    ENV: str = "development"
    WHISPER_MODEL: str = "tiny"
    DATABASE_URL: str = "postgresql+asyncpg://..."
    REDIS_URL: str = "redis://redis:6379/0"
    API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
    UPLOAD_CHUNK_BYTES: int = 1024 * 1024
    DEBUG: bool = False
```

## 9. 優先ロードマップ

1. **Phase 1 (1-2週)**: docker-compose + config整理 + print→logging
2. **Phase 2 (1-2週)**: GPU対応 + faster-whisper + tmpクリーンアップ
3. **Phase 3 (1週)**: GitHub Actions + API Key認証 + Cloudflare Tunnel
4. **Phase 4 (1週)**: Dozzle + UptimeRobot + デプロイスクリプト + DBバックアップ

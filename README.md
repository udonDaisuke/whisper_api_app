# setup
```bash
# ※WSL2　Ubuntu環境を想定しています。
# 実行権限を付与（最初の1回だけ）
chmod +x run.sh

# イメージをビルド（Dockerfileから whisper-api:latest を作成）
./run.sh build

# コンテナ起動（バックグラウンド）
# - var/cache を /cache にマウント（モデル等のキャッシュ永続化）
# - .env を読み込む（WHISPER_MODEL など）
# - 8000番ポートをホストに公開
# - 既に同名コンテナがあれば一度削除して置き換え
# - restart: unless-stopped で自動再起動
./run.sh up

# アプリのログをフォローして見る（Ctrl+C で抜ける）
./run.sh logs

# コンテナ内の Python を実行（例: バージョン表示）
# → run.sh が内部で `docker exec -it whisper-api python -V` を呼ぶ
./run.sh py -V

# コンテナにシェルで入る（デバッグ用）
# → run.sh が内部で `docker exec -it whisper-api bash` を呼ぶ
./run.sh shell

# コンテナを停止＆削除（イメージは消えない）
./run.sh down

```
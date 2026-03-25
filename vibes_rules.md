# VibesChain Rules

このファイルは `vibes init` によって自動生成された。VibesChain ワークフローのルールとコマンドリファレンスを記載する。

## 開発の軸

このリポジトリは VibesChain のワークフローで開発する。GitHub ISSUE・PR 操作はすべて `vibes` コマンド経由で行い、`gh` コマンドの直打ちは禁止。

## セットアップ

### settings.json の設定

```bash
cp .git/.vibes/settings.json.sample .git/.vibes/settings.json
# 必要に応じて設定値を編集する
```

### エージェントプロファイルの登録

```bash
vibes profile-install   # 自分のエージェントプロファイルを登録する
```

### セットアップ確認

```bash
vibes check-health      # 環境が正しく設定されているか確認する
```

## 基本的な開発フロー

**どんな作業でも、最初に ISSUE を作成してからブランチを切る。ISSUE のない作業は存在しない。**

```bash
vibes --help                      # コマンド一覧と使い方
vibes list-tasks                  # アサイン済みタスク一覧
vibes list-free                   # フリータスク一覧
vibes create-issue                # ISSUE 起票
vibes start-work <N>              # タスク取得・ブランチ作成（一括実行）
vibes create-pr                   # PR 作成
vibes review-pr <PR> approve      # PR 承認・マージ
```

## コミットメッセージ規約

コミット時に hook でフォーマットがバリデーションされる。

```
<Type><Scope>: Description [refs #N]

Why:
  <背景・理由>
What:
  <変更内容>
Now:
  <現在の状態>
```

詳細: `~/.vibes/docs/commit-message-spec.md`

## gh コマンド直打ち禁止

| やりたいこと | ❌ gh 直打ち | ✅ vibes コマンド |
|---|---|---|
| タスク一覧（アサイン済み） | `gh issue list --assignee @me` | `vibes list-tasks` |
| フリータスク確認 | `gh issue list --label free_task` | `vibes list-free` |
| ISSUE 作成 | `gh issue create` | `vibes create-issue` |
| ISSUE クローズ | `gh issue close <N>` | `vibes close-issue <N>` |
| タスク取得・ブランチ作成 | `gh issue edit` + `git checkout` | `vibes start-work <N>` |
| PR 作成 | `gh pr create` | `vibes create-pr` |
| PR マージ | `gh pr merge` | `vibes review-pr <PR> approve` |

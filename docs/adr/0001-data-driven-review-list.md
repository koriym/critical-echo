# ADR-0001: データ駆動型レビューリスト

## ステータス

承認・実装中

## コンテキスト

現在、`docs/index.html` にレビューリストがハードコードされており、レビュー追加のたびに手動編集が必要。

## 決定

### Phase 1（完了）

- `docs/_data/reviews.yml` にレビューメタデータを管理
- Jekyll の `site.data.reviews` でリスト自動生成
- 現在のデザイン（`index.html`）はそのまま維持

### Phase 2（実装中）

- `url_list.md` でレビュー済みURL管理
- GitHub Actions で `workflow_dispatch` トリガー
- トレンド自動収集 → 記事選定 → Claude API で批評生成

#### データソース

| プラットフォーム | エンドポイント |
|------------------|----------------|
| Zenn | `zenn.dev/api/articles?order=trend` |
| Qiita | `qiita.com/api/v2/items` |
| note | `note.com/recommend/rss` |
| Dev.to | `dev.to/api/articles?top=1` |
| Hacker News | HN Firebase API |

#### ワークフロー

```
workflow_dispatch
    ↓
scripts/fetch-trends.py（トレンド収集）
    ↓
url_list.md と照合（重複除外）
    ↓
48時間以内を優先、1記事選定
    ↓
Claude Code CLI で批評生成
    ↓
自動コミット＆プッシュ
```

### Phase 3（予定）

- 日次スケジュール実行
- 月次で `url_list.md` を `archive/YYYY-MM.md` にアーカイブ

## 言語方針

- 全てのレビュー記事は日本語
- 英語記事の場合は日本語で批評 + 著作権範囲内で要約

## 構成

```
url_list.md                  ← レビュー済みURLリスト
archive/
  YYYY-MM.md                 ← 月次アーカイブ
.github/workflows/
  generate-review.yml        ← ワークフロー
scripts/
  fetch-trends.py            ← トレンド収集スクリプト
docs/
  _data/
    reviews.yml              ← レビューメタデータ
  reviews/
    YYYY-MM-DD-slug.md       ← レビュー記事
  index.html                 ← Jekyllでリスト生成
```

## 結果

- レビュー追加時の編集箇所が `_data/reviews.yml` に集約
- CI自動化により手動作業を最小化
- 重複レビュー防止の仕組みが整備される

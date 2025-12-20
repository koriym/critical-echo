# ADR-0001: データ駆動型レビューリスト

## ステータス

承認

## コンテキスト

現在、`docs/index.html` にレビューリストがハードコードされており、レビュー追加のたびに手動編集が必要。

## 決定

### Phase 1（即時）

- `docs/_data/reviews.yml` にレビューメタデータを管理
- Jekyll の `site.data.reviews` でリスト自動生成
- 現在のデザイン（`index.html`）はそのまま維持

### Phase 2（半自動化）

- `url_list.md` でレビュー済みURL管理
- 手動でURL追加 → CI（Claude API）が批評生成

### Phase 3（全自動化）

- トレンド自動収集（Zenn, Hacker News等）
- 48時間以内の記事を優先
- 1日1記事生成
- 月次で `url_list.md` を `archive/YYYY-MM.md` にアーカイブ

## 言語方針

- 全てのレビュー記事は日本語
- 英語記事の場合は日本語で批評 + 著作権範囲内で要約

## 構成

```
url_list.md                  ← レビュー済みURLリスト（今月分）
archive/
  YYYY-MM.md                 ← 月次アーカイブ
docs/
  _data/
    reviews.yml              ← レビューメタデータ
  reviews/
    YYYY-MM-DD-slug.md       ← レビュー記事
  index.html                 ← Jekyllでリスト生成
```

## 結果

- レビュー追加時の編集箇所が `_data/reviews.yml` に集約
- 将来的にCI自動化への移行が容易
- 重複レビュー防止の仕組みが整備される

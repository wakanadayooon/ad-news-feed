# Ad News Feed

広告プラットフォーム（Google, Meta, Yahoo, LinkedIn, LINE, Bing）の最新情報を自動収集するシステム。

## 仕組み

1. **GitHub Actions** が毎日19:00 JST に自動実行
2. 48ソースの RSS フィードから新着記事を取得
3. YouTube チャンネルの新動画から字幕テキストを取得・要約
4. `feed.xml`（Feedly用RSS）と `calendar-data.js`（カレンダー用）を生成
5. **GitHub Pages** で公開

## 構成

```
.github/workflows/
  collect.yml          ← 毎日19:00 JST 自動実行
  classify.yml         ← 記事分類時に実行
scripts/
  collect_rss.py       ← RSS収集
  youtube_transcript.py ← YouTube字幕取得+要約（Hugging Face BART）
  generate_feed.py     ← feed.xml + calendar-data.js 生成
data/
  sources.yaml         ← 購読ソース一覧
  calendar.json        ← 記事データ+分類
docs/ (GitHub Pages)
  index.html           ← トップページ
  feed.xml             ← Feedly用RSSフィード
  calendar-data.js     ← ad-knowledgeカレンダー用データ
  transcripts/         ← YouTube字幕全文ページ
```

## カテゴリ（記事分類）

| カテゴリ | 意味 |
|---------|------|
| アップデート | 機能変更・仕様変更・新機能 |
| Tips | 運用ノウハウ・ベストプラクティス |
| 事例 | 成功事例・ケーススタディ |
| ニュース | イベント告知・業界動向 |
| スキップ | 不要 |

## 関連プロジェクト

- [ad-knowledge](https://github.com/wakana-official/ad-knowledge) — カレンダーページでこのデータを表示

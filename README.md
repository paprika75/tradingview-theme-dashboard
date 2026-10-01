# Theme Atlas — TradingViewテーマ分析 PCプロトタイプ

GitHub Pages向け、ビルド不要・外部ライブラリ不要の静的ダッシュボード。

## 単体プレビュー

`python3 scripts/build_preview.py`でCSS・スクリプト・デモデータを埋め込んだ単体HTML `preview.html` を生成できる。ブラウザで直接開ける。PC向けでスマホ対応は未実装。

## 起動

```bash
cd theme-dashboard
python3 -m http.server 4173 --bind 0.0.0.0
```

ブラウザで http://localhost:4173 を開く。`file://`で開くとJSONのfetchが動かないためHTTPで起動する。

## 実装済み

- 日米のテーマを独立表示。実際のテーマ名と構成銘柄を引継ぎ。
- Overview: Daily / Weekly、検索、Strong / 強化フィルタ、並び替え、過去日付選択。
- Theme Detail: 日次・週次スコア、提案重みの内訳、構成銘柄、Leader、TradingViewリンク。
- History: 最大4テーマの順位推移比較、保存した評価を再表示。
- 新規テーマ候補の詳細ダイアログ。
- About: 既存ロジック、提案事項、データの扱いと未接続部分。
- 相対パス、静的な4ページ、クエリによる市場・期間・日付の復元。

## データの状態

テーマ名・構成銘柄のみ実際のTradingViewテーマウォッチリストから取得。
**評価数値、順位、Leader、Stage、Setup、候補、履歴はすべて架空のデモ。投資判断用の実評価ではない。**
デモアーカイブはDaily 10日、Weekly 8週。生成時の営業日は平日の例で、取引所祝日は未接続。

過去の会話のv1は定性的な総合順位で固定スコア未実装。提案重み:
Daily Momentum40 / Breadth30 / Participation15 / Leader15。
Weekly Relative Strength35 / Trend Breadth30 / Trend Quality20 / Actionability15。
本プロトタイプはデモの0–100入力にその重みを適用。実指標正規化、欠損値、基準指数、Leader選定、最低構成数は本番実装前に確定が必要。

## ファイル

- index.html / theme.html / history.html / about.html
- app.js / styles.css
- data/theme-catalog.json — テーマ構成の取得時点のカタログ
- data/latest.json — 履歴マニフェストと最新キー
- data/daily/YYYY-MM-DD.json / data/weekly/YYYY-W##.json — immutable評価スナップショット
- data/candidates.json — 新規候補の表示例
- scripts/build_demo.py — 再現可能なデモ生成。scripts/watchlist-source.jsonを利用。
- tests/validate_data.py — スナップショット整合性検証（開発用）

## GitHub Pages公開

このフォルダの内容を公開用リポジトリのルートへ配置する。
GitHub Settings → Pages → Source: GitHub Actionsを選択し、含めた`.github/workflows/pages.yml`を利用。
`main`へのpushまたは手動実行で静的ファイルを配信。Actionsの対象はpublicのみをステージし、テストや元データを配信しない。
GitHub Pagesで公開済み: https://paprika75.github.io/tradingview-theme-dashboard/

## 検証状況

`python3 tests/validate_data.py`と`node tests/logic.cjs`が成功。順位・スコア・前回差分・構成銘柄、検索、フィルタ、履歴の時点制約、詳細ページ、単体バンドルをコード側で検証。2026年10月2日、公開したGitHub Pages上でPC画面をブラウザ検証済み。Daily / Weekly切替、日米切替、検索・検索0件、Strongフィルタ、候補ダイアログ、過去日付、テーマ詳細、日次10日・週次8週の履歴、最大4テーマ比較、保存評価の再表示、Aboutを確認。画面レイアウトも確認済み。数値は引き続きデモ。

## 次の実装

1. 実評価の計算・正規化を確定。
2. 市場別に確定終値と欠損値を管理した評価結果をJSON出力。
3. 最新マニフェストを更新し、過去の評価ファイルを保持。
4. スマホ向けのカード表示・ナビゲーションへ対応。

PC優先: 最小幅1180px。スマホ用の表示切替は未実装。
認証トークン、TradingView Cookie、個人のポジション・Entry / Stop情報は含めない。

# Theme Atlas — TradingViewテーマ分析ダッシュボード

PC優先の静的Webアプリ。公開URL: https://paprika75.github.io/tradingview-theme-dashboard/

## 実装した判断フロー

Market Health → Institutional Focus → Theme Translation → New Entry Opportunities / Active Theme Health → Theme Landscape → Theme Rotation。

ダークUI、US / Japan、Daily / Weekly、過去評価日切替、検索・フィルタ・並び替え、テーマ詳細、Leader Top 5、VCP / CWH / Base Breakout / Pullback・Retest、TradingViewリンク、順位Heatmap、選択テーマのみの折れ線、Market Driver History、新規テーマ候補を実装。
保有監視の選択は市場別のlocalStorageに保存。公開データにユーザーのポジションを含めない。

## データの状態

**数値、順位、Leader、Stage、Setup、AI解釈、保有例、過去の判断文章はすべてMock。実際の市場評価・事前予測ではない。**

既存TradingViewカタログのテーマ名・構成銘柄を維持。Energy / Oil Services / Gold Miners / Utilities等は、TV未登録のMock拡張例と明示。
Daily 10評価日、Weekly 8評価週。祝日カレンダーは未接続。AI例は`kind: retrospective-mock-fixture`と実際の生成時刻を保存し、過去の事前予測と区別する。

## 構成

```text
app.js                    ページ・URL・端末内監視状態
lib/data.mjs              読込・時点結合・失敗表示
lib/logic.mjs             定量判定
lib/views.mjs             共通データを描画
config/scoring.json       ウェイト・閾値・版番号
data/latest.json          Mock / Liveルーター
data/mock/latest.json     履歴マニフェスト
data/mock/daily/           日次評価・quantitative / scores
data/mock/weekly/          週次評価・quantitative / scores
data/raw/mock/            合成Raw観測
data/analysis/mock/       独立した日付付きAI例・confidence
```

旧`data/daily/`・`data/weekly/`は変更せず、`data/legacy-manifest.json`から参照可能。新UIはv2を使用する。
定量スコアにAIのMacro / Institutional Alignmentを直接加算しない。AI材料は別表示して文脈判断を検証できる構造。

## 初期評価ロジック

- Market Health: Trend30 / Institutional Action20 / Breadth20 / Leadership20 / Breakout Quality10。
- Daily / Weekly: 既存の提案重みを維持。全構成を詳細表示。
- Leader: RS30 / Trend20 / Structure15 / Liquidity10 / Accumulation10 / Breakout10 / Fundamental5。
- Opportunity: Weekly25 / Daily Acceleration20 / Breadth15 / Leader15 / Ready Setup15 / Market Health10。Dailyデータ・Weekly強度・市場環境・Ready Setup・非Extendedをゲート判定。
- Active Health: 3–5営業日の短期変化と3週間の中期変化を分離。短期悪化だけならWATCH。中期スコア低下＋200DMA維持率低下を加えてDETERIORATING。

Market Healthカテゴリ値やRS・Stageの本番用正規化/検出は未実装。上記は検証前の初期設計。閾値とウェイトは設定ファイルで変更可能。1桁スコアの丸めはhalf-upで統一し、欠損入力は点数を—にする。

## 時点・更新状態

URL例: `?market=us&period=daily&date=2026-10-01`、`theme.html?id=us-6&market=us&period=daily&date=2026-10-01`。従来の大文字US / JPにも対応。
選択日以前のDaily / Weekly・AIファイルを使い、未来の評価を混ぜない。ランキング差分は保存済みの前回評価から計算。履歴ファイルを読み込めない場合はHeatmapの—と折れ線の切断で表現。
MockはMOCK DATA、過去はARCHIVE。評価の読込失敗で過去データを使うとSTALE DATAと理由・最終成功日を表示。Live更新予定を超過した場合もSTALE。IBD Referenceは未取得、Exposure・DIVERGENCEは未判定。

## 起動・検証

```bash
python -m http.server 8000
node --test tests/v2.test.mjs
python tests/validate_data.py
```

http://localhost:8000 を開く。ES modulesとJSONのfetchを使用するためHTTPで配信する。
`node tests/logic.cjs`もv2テストへ転送。Pythonテストは旧アーカイブの不変性・整合性を検証する。
`python scripts/build_v2_mock.py`は同一内容なら再現可能。既存評価やAIファイルを異なる内容で上書きしようとすると停止する。公開後の変更は新しい版/履歴として追加する。旧v1生成・単体プレビューのスクリプトは誤使用を防ぐ案内を表示する。

## GitHub Pages

Pages SourceはGitHub Actions。`main`へのpush・手動実行でテスト→静的配信。依存ライブラリ・バックエンド・APIキーは不要。HTML / CSS / JS / lib / config / dataのみ配信する。

## 次の段階・制約

1. 実OHLCVとBreadth取得元、市場別確定時刻・祝日・欠損値処理を決める。
2. RS / Stage / Setup / Distribution / Breakout等の実数計算と検証を追加する。
3. ニュース・イベント・決算の出典付きAI生成をActions側で行い、日付付きファイルを追記する。秘密情報はGitHub Secretsで管理し、静的ページへ渡さない。
4. 同一データ処理を使うスマホ用テーマカード・ナビゲーションを追加する。

GitHub Pages単体では秘密キーを使うデータ取得やAI生成を実行しない。取得/生成は将来のActions等へ分離する。現時点のActionsは配信のみで、データ自動更新は未接続。
PC1280–1440px基準。横幅の多いテーブルは独立スクロール。スマホ専用UIは未実装。

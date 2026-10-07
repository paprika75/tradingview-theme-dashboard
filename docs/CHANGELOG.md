# Theme Atlas — Changelog

実装・検証・仕様変更の履歴を時系列で記録する。

## 2026-10-07 — Lifecycle誤判定修正 / Pre-Setup抽出基盤

- Entry未突破をBREAKOUTとする符号判定を廃止。共通のデータ判定へ移行。
- DOM数値の「—」を0へ変換する処理を廃止。旧Pullback/Retestの曖昧な状態は未判定。
- Entry候補フィルタの強制解除を廃止し、Lifecycleフィルタとの併用とURL保存を追加。
- Setup Type / Lifecycle / Entry判定・形成度を分離し、推定と保存状態を明示。
- 分析ダイアログのFORMING等の元ステータスを保持。
- 公開ファイル生成にLifecycle moduleと依存関係のcontent hashを追加。
- 一次Watchlist専用のPre-Setup抽出CLIと独立設定1.0.0を追加。日付付きUniverse、収縮・Pivot・形成度、状態の追記保存、欠損/除外理由を扱う。
- 既存テーマ・市場評価・参考投資比率・過去snapshotは変更しない。
- 新しいPre-Setup評価の実データ収集・画面接続・正式Setup昇格は継続作業。
- 回帰検証: Node34件 / Python43件。#9に不具合修正を分離し、#10〜#12へ不足作業を追加。

## 2026-10-07 — Setup Type / Post-Breakout Lifecycle分離

Setupのチャート型とブレイク後の現在状態を別軸へ変更。

- `setup_type`: 起点のチャート型。現行採用は VCP / CWH / Base Breakout。ブレイク後も保持。
- `lifecycle`: `SETUP / BREAKOUT / EXTENDED / PULLBACK / RETEST / 3WT / TIGHT / ASCENDING_BASE / FAILED_BREAKOUT`。
- OverviewのSetup表をSetup Type / Lifecycle分離表示へ変更し、Lifecycle filterを追加。
- Legacy snapshotは遡及上書きせず、元setup_typeを復元できない場合は未判定表示。
- `🇺🇸セットアップ` / `🇯🇵セットアップ` はsetup_type軸を維持。
- `❤️ブレイクアウト` / `💙ブレイクアウト` はlifecycle軸へ再構成。
- 既存のBreakout銘柄は推測で再分類せず、従来状態を保持してBREAKOUT区分へ移行。
- Issue #6をPost-Breakout Lifecycle統合まで含む内容へ更新。

現時点では新規Observed snapshotへの `setup_type` / `lifecycle` 永続化と、Breakout後Lifecycleの自動候補判定は未実装。Issue #6で継続する。

## 2026-10-07 — README / docs再編

- READMEを概要・起動・主要構成・参照先に絞る方針へ変更。
- 変更履歴を `docs/CHANGELOG.md` に分離。
- 判断・運用フローを `docs/WORKFLOW.md` に分離。
- TradingView標準Stock Screener → 一次Watchlist → Pre-Setup → Pivot REVIEW alert → 正式Setupの運用仕様を文書化。

## 2026-10-07 — 参考投資比率

上部要約とMarket Outlook内に参考投資比率を追加。

- IBDの公開説明の5レンジ（0–20 / 20–40 / 40–60 / 60–80 / 80–100%）を参考にした独自算出。
- 対象は各市場の株式投資用資金（株式＋待機現金）に対する株式比率。
- 総資産配分、実際の保有割合、公式IBDの当日値ではない。
- 監視銘柄、Momentum Health、Theme scoreは使用しない。
- 設定: `config/market-exposure.json`
- 版: `1.0.0-index-exposure`

初期ルール:

- Correction: 0–20%
- Under Pressure: 40–60%を基本
- 50DMA以下 / Distribution Days 7日以上 / 5営業日で3日以上集中時は20–40%
- Confirmed Uptrend後5営業日未満: 20–40%
- 5–9営業日: 40–60%
- 10営業日以上: 60–80%
- 15営業日以上かつ50/200DMA上、50DMA上向き、Distribution Days 2日以下: 80–100%

価格構造が未確認なら40–60%以下に制限。必要指数の低いレンジを採用する。出来高・FTD・確定営業日が不足する場合は未判定。

検証: Node 27件 / Python 31件。

## 2026-10-07 — Market Outlook / Distribution Days / Momentum Health

第1セクションを以下の順に再構成。

1. Market Outlook
2. Distribution Days
3. Momentum Health

上部市場要約はMomentum Health scoreではなくMarket Outlookを表示。市場判定に監視テーマ・個別銘柄・Leader scoreは使用しない。

指数:

- US: `SP:SPX`, `NASDAQ:IXIC`
- Japan: `TSE:TOPIX`, `TVC:NI225`

TradingViewから750営業日を取得し、確定日までに制限。

日本指数は出来高未取得のため、Distribution Day / FTD / Market classificationは未判定とし、価格方向のみ別表示。ETF出来高を指数出来高の代理にはしない。

設定: `config/market-outlook.json`  
版: `1.0.0-index-outlook`

主な独自ルール:

- Distribution Day: 丸め前で下落0.2%以上 + 前日より出来高増加
- 25営業日経過または日中高値で5%回復で失効
- FTD: Rally Day 1からDay 4以降、+1.25%以上 + 出来高増加 + 起点安値維持
- FTD成立で有効Distribution Daysをリセット
- 起点 / FTD安値割れでConfirmed Uptrendを無効化
- 2日連続50DMA割れ、21日高値から8%以上下落、新規200DMA割れもCorrection開始条件
- Under Pressure: 50DMA割れ、Distribution Days 5日以上、または5営業日に3日の集中

これはIBD公式判定の再現ではなく独自ルール。Stalling Day等の裁量要素は含めない。

検証: Node 23件 / Python 21件。

## 2026-10-07 — Momentum Health表示名

旧 `Market Health` を `Momentum Health` に変更。

- 監視銘柄群のBreadth / Stage 2比率と指数トレンド・出来高proxyを合成する補助指標であることを明記。
- 市場全体の健全性やIBD Market Outlookそのものとは扱わない。
- 指数評価と監視群評価の内訳を表示名で区別。
- 計算式、閾値、保存済み評価、内部data key、anchorは維持。

## 2026-10-06 — US / Japanページと3本柱の要約

市場別ページを追加。

- US: `us.html`
- Japan: `japan.html`

共通のdata loading、quant logic、8主要セクションを利用。URL pathで市場を固定し、旧 `index.html?market=us/jp` は市場別ページへ移動。

上部要約を3本柱化。

1. 市場環境・参考投資比率
2. 新規投資候補のテーマと銘柄
3. 継続監視・警戒

ACTIVE THEME HEALTHは全テーマを評価し、Healthy / Watch / Deteriorating / Unassessedを分離。入力不足を警戒件数に含めない。

公開サイトでは実際の保有銘柄・取得価格・数量・損益を扱わない。localStorageの監視テーマ選択は公開要約の評価から独立。

検証: Node 20件 / Python 8件。1280px / 1440pxで横はみ出しなし。

## 2026-10-06 — Observed Technicals v3

Demoを保持したままObserved / Demo切替を追加。

ObservedはTradingView MCPから取得した分割調整済み確定日足を利用。

- 初回Daily: 2026-10-05
- 初回Weekly: 2026-10-02
- Raw observation: `observations/2026-10-06/ohlcv.json`

算出:

- 21EMA
- 50 / 150 / 200SMA
- 確定週40SMA
- returns
- RVOL
- 52週高値 / 安値
- RS proxy
- Stage 2 proxy

RSは指数比リターン 63 / 126 / 189 / 252営業日を40 / 20 / 20 / 20で加重し、現在の監視Universe内でpercentile化。IBD RS Ratingや全市場順位ではない。

Breadthは監視銘柄群内。2銘柄以上かつ必要履歴を持つ有効構成80%以上のテーマだけrank対象。

設定: `config/versions/3.0.0-observed-technicals.json`

Base / Pullbackは価格・MA・RVOLによるrule candidate。ReadyはStage 2、形成条件、Entry/Stop risk 8%以内、価格位置、出来高で選別。VCP / CWHの確定検出は未実装で、手動chart確認を必要とする。

ObservedではAI / Macro translation / new theme discoveryは未接続と表示し、Mock文章を混ぜない。

Build:

```bash
python scripts/build_live.py --input observations/YYYY-MM-DD/ohlcv.json --activate
node --test tests/*.test.mjs
python tests/test_live.py
python tests/validate_data.py
```

既存snapshotの異内容上書きは拒否。自動収集・scheduleは未接続。最終取得から36時間超でSTALE。

検証: Node 17件 / Python 8件。Observed / Demo、US / Japan、Daily / Weekly、Leader / Setup、Theme detailを公開画面で確認。

## 2026-10-06 — 引継ぎ確認とv2補完

開始時 `main / eb68a4d51734b9eca554d12901012e4312b88ed3`。GitHub上のv2を基準として補完。

- 既存Momentum Health、Institutional Focus、Translation、Opportunity、Active Health、Landscape、History、Theme detail、local watch stateを維持。
- Theme Leader / Setupをトップ画面にも追加。
- Setup candidateはTheme Opportunityに加え、Stage 2 / Ready / 有効Entry・Stop / 非Extendedをgateとした。
- Entry候補が0でも全Setupに切り替えて形成中候補を確認可能。
- Weeklyでは保存済み週次水準を表示。
- 過去Theme score / setting / snapshotは再計算しない。

検証: Node 14件 / Python archive 2件、GitHub ActionsとPages成功。1280px / 1440pxで主要panelの横はみ出しなし。

## 2026-10-02 — PC公開画面の検証

GitHub Pages上で以下を確認。

- US / Japan
- Daily / Weekly
- 過去日付
- 検索 / 0件
- Entry filter
- sort
- watch themeのlocalStorage保存 / 解除
- Theme detail
- TradingView link
- candidate dialog
- 最大4テーマline chart
- AI judgment history
- scoring settings

1280px / 1440pxでpage全体・主要grid・cardに意図しない横はみ出しなし。多列tableはpanel内scroll。

CSSとES modules dependencyをcontent hashでversioningし、cache混在を抑制。過去評価は保存済みsetting versionを利用し、現在設定で再計算しない。

# Theme Atlas — TradingViewテーマ分析ダッシュボード

TradingViewの市場・テーマ・個別銘柄データを整理し、**市場環境 → テーマ → Leader → Pre-Setup / Setup** の順で投資候補を確認するための開発中ダッシュボード。

公開URL: https://paprika75.github.io/tradingview-theme-dashboard/

> **このREADMEは開発トップページです。**  
> 現在の方針・未実装項目・次にやることをここに集約します。  
> 詳細仕様は [Workflow](docs/WORKFLOW.md)、変更履歴は [Changelog](docs/CHANGELOG.md) を参照してください。

---

## 現在決まっている方針

### 1. 市場環境

市場全体の判断と、監視銘柄群の強さを分離する。

- **Market Outlook**: 主要指数のみで判定
- **Distribution Days / FTD**: 指数の価格・出来高を使う独自ルール
- **参考投資比率**: Market Outlookから独立ルールで算出
- **Momentum Health**: 監視銘柄群のBreadth / Stage 2等を見る補助指標

米国は `SP:SPX` / `NASDAQ:IXIC` を使用。  
日本は `TSE:TOPIX` / `TVC:NI225` を使用するが、指数出来高の入力が未解決のためDistribution Days / FTDは現時点で未判定。

### 2. テーマ・銘柄選別

判断フロー:

```text
Market Outlook
→ Distribution Days / FTD
→ Momentum Health
→ Institutional Focus
→ Theme Translation
→ New Entry Opportunities / Active Theme Health
→ Theme Landscape
→ Theme Leaders
→ Pre-Setup / Setups
→ Theme Rotation
```

### 3. Swing Setup

採用するSetupは3種類だけ。

1. **VCP**
2. **Cup With Handle (CWH)**
3. **Base Breakout**

GenericなNew High Breakoutは独立カテゴリにしない。

### 4. 一次スクリーニング

TradingView標準Stock Screenerを週1回手動で実行する。

理由: TradingView MCPの `run_screener` は429が発生することがあり、現時点では全市場スクリーニングの自動運用に依存しない。

一次Watchlist:

- `🇺🇸一次スクリーナー`
- `🇯🇵一次スクリーナー`

一次では広く拾い、150SMA、200SMA傾き、RS、ベース構造などは後段で評価する。

### 5. Pre-Setup

一次Watchlistから日足OHLCVを確認し、ブレイク前候補を抽出する。

重視する項目:

- 直近高値 / 抵抗帯までの距離
- 10〜15日の値幅収縮
- ATR contraction
- Volume dry-up
- 高値・安値の切り上げ
- 明確なPivot候補
- Relative Strength

固定60日Base DepthはHard Filterにしない。

状態:

- **Ready**: Pivotまで概ね3%以内
- **Near**: 3〜7%
- **Forming**: それ以上でも形成が進行中

Pre-Setup Watchlist:

- `🇺🇸プレセットアップ`
- `🇯🇵プレセットアップ`

### 6. Pivotアラート

Pre-Setup追加時にTradingView価格アラートを設定する。

```text
REVIEW | TICKER | Pivot PRICE
```

- `Price > Pivot`
- 1分判定
- 初回発火で自動停止
- Mobile Push / Popup ON

**REVIEW発火は自動Buyではない。**  
発火後にSetup構造、出来高、Gap、Stop、Risk、市場環境を再評価する。

### 7. 正式Setup

Pre-Setupからチャート確認後、VCP / CWH / Base Breakoutに分類して正式Setupへ昇格する。

確認順:

```text
Setup構造
→ Standard Pivot
→ Early / Cheat Entry（必要な場合）
→ 構造的Stop
→ Entry-to-Stop Risk
→ Extended判定
```

---

## 開発ロードマップ / Issues

### P0 — まず完成させる

- [#1 Watchlist起点のPre-Setup抽出ロジック](https://github.com/paprika75/tradingview-theme-dashboard/issues/1)
- [#2 Pre-Setupから正式Setupへの判定・昇格フロー](https://github.com/paprika75/tradingview-theme-dashboard/issues/2)
- [#3 Pivot REVIEWアラートのライフサイクル管理](https://github.com/paprika75/tradingview-theme-dashboard/issues/3)

### P1 — 実運用を安定させる

- [#4 RS Rank proxyを本番用Universeで計算](https://github.com/paprika75/tradingview-theme-dashboard/issues/4)
- [#5 Observedデータ更新フローを定期運用化](https://github.com/paprika75/tradingview-theme-dashboard/issues/5)
- [#6 DashboardにPre-Setup / Setup監視状態を統合](https://github.com/paprika75/tradingview-theme-dashboard/issues/6)
- [#7 日本市場Market Outlookの出来高データ源を決定](https://github.com/paprika75/tradingview-theme-dashboard/issues/7)

### P2 — 精度向上

- [#8 EPS・売上成長を補助スコアとして追加](https://github.com/paprika75/tradingview-theme-dashboard/issues/8)

---

## 現在できていること

- US / Japanページ
- Daily / Weekly
- Observed / Demo
- Market Outlook
- Distribution Days / FTDロジック（米国）
- 参考投資比率
- Momentum Health
- Theme Landscape / Opportunity / Active Health
- Theme Leaders
- Setup候補表示
- TradingView OHLCVを使うObserved評価
- TradingView Watchlistの読み書き
- TradingView価格アラート作成
- 過去snapshot / rule versionの保存

---

## まだ手動のもの

- TradingView標準Stock Screenerの週次実行
- 一次Watchlistへの結果投入
- VCP / CWH / Base Breakoutの最終チャート確認
- TradingView MCP認証を必要とするObservedデータ取得

---

## データ上の原則

- 過去snapshotを現在ルールで遡及上書きしない
- Future dataを過去評価へ混ぜない
- 欠損データを0点として扱わない
- Mock / DemoとObservedを混在させない
- 市場環境と監視銘柄群の評価を混同しない
- 独自指標をIBD公式指標として表現しない

---

## 主な構成

```text
app.js                    page / URL / local state
lib/data.mjs              data loading / point-in-time join / status
lib/logic.mjs             quantitative logic
lib/views.mjs             shared rendering
config/scoring.json       current weights / thresholds
config/market-outlook.json
config/market-exposure.json
config/versions/          immutable historical rule versions
data/                     generated / archived evaluation data
observations/              captured TradingView observations
scripts/                   build scripts
tests/                     Node / Python tests
docs/WORKFLOW.md           current analysis / screening workflow
docs/CHANGELOG.md          implementation history
```

---

## Local起動

```bash
python -m http.server 8000
```

ブラウザで `http://localhost:8000` を開く。

ES modulesとJSON fetchを使用するため、HTMLを直接開かずHTTP経由で配信する。

### Tests

```bash
node --test tests/*.test.mjs
python tests/test_live.py
python tests/validate_data.py
```

---

## ドキュメント

- **Current workflow / rules**: [docs/WORKFLOW.md](docs/WORKFLOW.md)
- **Implementation history**: [docs/CHANGELOG.md](docs/CHANGELOG.md)

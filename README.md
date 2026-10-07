# Theme Atlas — TradingViewテーマ分析ダッシュボード

TradingViewの市場・テーマ・個別銘柄データを整理し、**市場環境 → テーマ → Leader → Pre-Setup / Setup → Post-Breakout** の順で投資候補を確認する開発中ダッシュボード。

公開URL: https://paprika75.github.io/tradingview-theme-dashboard/

詳細仕様は [Workflow](docs/WORKFLOW.md)、Setup状態モデルは [Setup State](docs/SETUP_STATE.md)、変更履歴は [Changelog](docs/CHANGELOG.md) を参照。

---

## 現在の判断フロー

```text
Market Outlook
→ Distribution Days / FTD
→ Momentum Health
→ Institutional Focus / Theme Translation
→ Theme Landscape / Theme Leaders
→ Pre-Setup
→ Formal Setup
→ Post-Breakout Lifecycle
→ Theme Rotation
```

市場全体の判定と監視銘柄群の強さは分離する。

- **Market Outlook**: 主要指数のみ
- **Distribution Days / FTD**: 指数価格・出来高による独自ルール
- **参考投資比率**: Market Outlookから独立算出
- **Momentum Health**: 監視銘柄群のBreadth / Stage 2等をみる補助指標

---

## Swing Setup

正式採用するSetup Type:

1. **VCP**
2. **Cup With Handle (CWH)**
3. **Base Breakout**

`setup_type` と `lifecycle` は別軸。

```text
setup_type: VCP / CWH / Base Breakout

lifecycle:
SETUP
→ BREAKOUT
→ EXTENDED / PULLBACK / RETEST
→ 3WT / TIGHT / ASCENDING_BASE
→ FAILED_BREAKOUT
```

TradingViewでは、`🇺🇸セットアップ` / `🇯🇵セットアップ` をSetup Type軸、`❤️ブレイクアウト` / `💙ブレイクアウト` をLifecycle軸で管理する。

### 保存モデル

新規Observed snapshotでは以下を個別銘柄へ保存する。

```text
setup_type / setupConfirmed / setupTypeSource
lifecycle / lifecycleConfirmed / lifecycleSource
lifecycleCandidate / lifecycleCandidateReasons
setupRegistryAsOf / lifecycleRuleVersion
```

手動チャート確認済みの状態を自動判定で上書きしない。自動ロジックは `lifecycleCandidate` のみを提案し、TradingViewリストの移動はチャート確認後に行う。

手動状態は日付付きで保存する。

```text
data/setup-state/registry/YYYY-MM-DD.json
```

評価日以前のregistryだけをsnapshotへjoinし、未来情報を過去評価へ混ぜない。

---

## Screening / Pre-Setup

一次スクリーナーはTradingView標準Stock Screenerを週1回手動実行。

- `🇺🇸一次スクリーナー`
- `🇯🇵一次スクリーナー`

一次Watchlistから、収縮・ATR・Volume Dry-up・高値安値構造・Pivot距離などでPre-Setup候補を抽出する。

- **Ready**: Pivotまで概ね3%以内
- **Near**: 3〜7%
- **Forming**: それ以上でも形成進行中

格納先:

- `🇺🇸プレセットアップ`
- `🇯🇵プレセットアップ`

正式Setup昇格時にSetup Type / Pivot / Stop / Riskをチャート確認する。

---

## Pivot alert

```text
REVIEW | TICKER | Pivot PRICE
```

REVIEW発火はBuyシグナルではない。発火後にSetup構造、出来高、Gap、Stop、Risk、市場環境を再評価する。

---

## 現在できていること

- US / Japan、Daily / Weekly、Observed / Demo
- Market Outlook / Distribution Days / FTD（米国）
- 参考投資比率 / Momentum Health
- Theme Landscape / Theme Leaders / Setup表示
- Setup Type / Lifecycle / Entry判定・形成度の分離表示
- Lifecycle filter + URL状態保存
- 一次Watchlist用Pre-Setup抽出CLI
- 日付付きSetup registry
- Observed snapshotへの `setup_type / lifecycle` 永続化
- `lifecycleCandidate` 自動候補判定
- Pre-Setup保存評価のDashboard読み取り（実データ収集は未完）
- 昇格要件・Setup episode・Lifecycle別Entry Planの保存モデルと検証
- TradingView Watchlistの読み書き
- Pivot価格アラート
- append-only snapshot / versioned rules

---

## まだ手動のもの

- TradingView標準Stock Screenerの週次実行
- 一次Watchlistへの投入
- VCP / CWH / Base Breakoutの最終チャート確認
- `lifecycleCandidate` の確認とTradingView Lifecycleリストへの反映
- Lifecycleに応じたEntry / Stop / Riskの再評価
- REVIEW alert状態とDashboardの完全同期
- TradingView MCP認証を必要とするObservedデータ取得

---

## 次の実装優先順位

1. **#1 / #2 / #6** Pre-Setup実データ収集 → 正式Setup確認記録 → Dashboard表示
2. **#6** LifecycleごとのEntry / Stop / Riskを確認・保存して表示
3. **#3** Pivot REVIEW alertの状態管理
4. **#5** Observed更新フローの定期運用化

関連Issues: [#1](https://github.com/paprika75/tradingview-theme-dashboard/issues/1) / [#2](https://github.com/paprika75/tradingview-theme-dashboard/issues/2) / [#3](https://github.com/paprika75/tradingview-theme-dashboard/issues/3) / [#5](https://github.com/paprika75/tradingview-theme-dashboard/issues/5) / [#6](https://github.com/paprika75/tradingview-theme-dashboard/issues/6)

---

## Observed build

通常運用ではSetup Stateをjoinするwrapperを使う。

```bash
python scripts/build_live_with_setup_state.py \
  --input observations/YYYY-MM-DD/ohlcv.json \
  --activate
```

`scripts/build_live.py` はテクニカル計算core。

---

## Tests

```bash
node --test tests/*.test.mjs
python tests/validate_data.py
python tests/test_live.py
python tests/test_market_outlook.py
python tests/test_market_exposure.py
python tests/test_pre_setup.py
python tests/test_setup_lifecycle.py
python tests/test_live_setup_state.py
python tests/test_setup_journey.py
```

Pages deploy前にも同じLifecycle回帰テストを実行する。

---

## データ上の原則

- 過去snapshotを現在ルールで遡及上書きしない
- Future dataを過去評価へ混ぜない
- 欠損データを0点として扱わない
- Mock / DemoとObservedを混在させない
- 市場環境と監視銘柄群の評価を混同しない
- 独自指標をIBD公式指標として表現しない
- 自動候補とチャート確認済み状態を区別する

---

## Documents

- [Workflow](docs/WORKFLOW.md)
- [Setup State Model](docs/SETUP_STATE.md)
- [Setup Journey / Entry Plan](docs/SETUP_JOURNEY.md)
- [Changelog](docs/CHANGELOG.md)

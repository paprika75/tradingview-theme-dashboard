# Setup Type / Lifecycle State Model

この文書は、Theme Atlasにおける個別銘柄のSetup TypeとLifecycleの保存・更新ルールを定義する。

## 1. 基本原則

チャート型と現在状態を別軸で扱う。

- `setup_type`: どのチャート型から始まったか。原則としてブレイク後も保持する。
- `lifecycle`: 現在どのフェーズにいるか。
- `lifecycleCandidate`: OHLCVから機械判定した現在状態の候補。

**手動チャート確認済みの状態を、自動ロジックで上書きしない。**

自動判定は候補生成に使い、TradingViewリストまたは明示的なチャート確認で確定した状態を最終状態とする。

---

## 2. Setup Type

現行の正式Setup Type:

- `VCP`
- `CWH`
- `Base Breakout`

`Pullback / Retest / 3WT / Tight` などはSetup TypeではなくLifecycleである。

自動ルールでBase候補を検出しただけの場合は `setupConfirmed=false` とする。

TradingViewの正式Setupリストでチャート確認済みの場合は `setupConfirmed=true` とする。

---

## 3. Lifecycle

正規値:

```text
SETUP
BREAKOUT
EXTENDED
PULLBACK
RETEST
3WT
TIGHT
ASCENDING_BASE
FAILED_BREAKOUT
UNASSESSED
```

基本遷移:

```text
SETUP
  ↓ Pivot突破
BREAKOUT
  ├─ EXTENDED
  ├─ PULLBACK
  ├─ RETEST
  ├─ 3WT
  ├─ TIGHT
  ├─ ASCENDING_BASE
  └─ FAILED_BREAKOUT
```

FAILED_BREAKOUT後に新しいBaseを形成した場合は、新しいSetupとして再評価する。過去の失敗判定を書き換えない。

---

## 4. 保存フィールド

新規Observed snapshotでは個別銘柄の `quantitative` に以下を保存する。

```text
setup_type
setupConfirmed
setupTypeSource
setupRegistryAsOf

lifecycle
lifecycleConfirmed
lifecycleSource

lifecycleCandidate
lifecycleCandidateReasons
lifecycleRuleVersion
```

### Sourceの意味

- `TV_SETUP_LIST`: TradingView正式Setupリストで確認済み
- `TV_BREAKOUT_LEGACY_ORIGIN`: 旧Breakoutリストの元分類から保存したSetup Type
- `TV_LIFECYCLE_MIGRATION`: 旧BreakoutリストからLifecycle方式へ移行した状態
- `RULE_CANDIDATE`: OHLCVルールによる候補
- `UNASSESSED`: 判定材料不足

移行時にBREAKOUTへ置いた銘柄は、元Setup Typeは保存するが `lifecycleConfirmed=false` とする。これは「現在もBreakout直後」と確認した意味ではない。

---

## 5. Point-in-time registry

手動確認状態は日付付きregistryへ保存する。

```text
data/setup-state/registry/YYYY-MM-DD.json
data/setup-state/registry/manifest.json
```

snapshot生成時には、評価日以前で最も新しいregistryだけをjoinする。

```text
registry.asOf <= snapshot.asOf
```

未来のTradingViewリスト状態を過去snapshotへ混ぜない。

既存snapshotは遡及更新しない。

---

## 6. Lifecycle candidateの判定順

自動候補は `scripts/setup_lifecycle.py` で算出する。

優先順位:

1. `FAILED_BREAKOUT`
2. `RETEST`
3. `PULLBACK`
4. `3WT`
5. `ASCENDING_BASE`
6. `TIGHT`
7. `EXTENDED`
8. `BREAKOUT / SETUP`
9. `UNASSESSED`

RETEST / PULLBACKを3WT等より先に判定する。支持テスト中の銘柄を、単に週足終値が締まっているという理由でContinuation Setupへ上書きしないため。

### 現行ルール v1.0.0

- Failed Breakout: Pivotから3%以上下 + 50DMA下
- Retest: Entry/Pivotから±3%
- Pullback: 21EMAから-2〜+3%、50DMA上、RVOL <= 1.2
- Extended: Entry/Pivotまたは21EMAから+10%以上
- Tight: 直近5営業日の値幅5%以内
- Three Weeks Tight: 直近3完了週の隣接終値変化が各1.5%以内
- Ascending Base candidate: 60営業日を3区間に分け、安値切り上げ・各区間の値幅22%以内・期間高値から5%以内

これらは**候補抽出ルールであり、チャートパターンの確定判定ではない**。

---

## 7. TradingViewとの役割分担

### Setup Type軸

- `🇺🇸セットアップ`
- `🇯🇵セットアップ`

正式Setup Typeを保存する。通常は `lifecycle=SETUP`。

### Lifecycle軸

- `❤️ブレイクアウト`
- `💙ブレイクアウト`

以下で管理する。

```text
BREAKOUT
EXTENDED
PULLBACK
RETEST
3WT
TIGHT
ASCENDING BASE
FAILED BREAKOUT
```

自動 `lifecycleCandidate` だけを理由にTradingViewリストを移動しない。チャート確認後に変更する。

---

## 8. Observed build

通常のObserved snapshot生成は、Setup Stateをjoinするwrapperを使う。

```bash
python scripts/build_live_with_setup_state.py \
  --input observations/YYYY-MM-DD/ohlcv.json \
  --activate
```

`scripts/build_live.py` はテクニカル計算のcore。通常運用ではwrapperを入口とする。

wrapperはimmutable snapshotを書き出す直前にSetup registryとLifecycle candidateをjoinする。

---

## 9. データ整合性

以下をテストで固定する。

- 手動registryが自動候補より優先される
- 自動候補は別fieldに残る
- 未来registryを過去snapshotへjoinしない
- 同じ入力の再生成結果は同一
- Setup TypeとLifecycleを混同しない
- RETEST / PULLBACKの優先順位を維持する

関連テスト:

```text
tests/setup-state.test.mjs
tests/test_setup_lifecycle.py
tests/test_live_setup_state.py
```

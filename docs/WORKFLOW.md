# Theme Atlas — Workflow

この文書を、Theme Atlas の**判断フロー・銘柄抽出・TradingView運用の Single Source of Truth** とする。

## 1. 全体の判断フロー

```text
Market Outlook
  ↓
Distribution Days / FTD
  ↓
Momentum Health
  ↓
Institutional Focus
  ↓
Theme Translation
  ↓
New Entry Opportunities / Active Theme Health
  ↓
Theme Landscape
  ↓
Theme Leaders
  ↓
Pre-Setup / Setups
  ↓
Post-Breakout Lifecycle
  ↓
Theme Rotation
```

市場環境と個別銘柄評価は分離する。

- **Market Outlook**: 主要指数のみで市場方向を判定する。
- **Distribution Days / FTD**: 指数の価格・出来高から独自ルールで算出する。
- **Momentum Health**: 監視銘柄群のBreadth / Stage 2比率等を用いる補助指標。市場全体そのものとは扱わない。
- **Theme / Leader / Setup**: 市場評価とは独立してテーマ強度・個別銘柄候補を評価する。

---

## 2. Swing銘柄抽出ワークフロー

現時点で正式採用するSetup Typeは次の3種類。

1. **VCP**
2. **Cup With Handle (CWH)**
3. **Base Breakout**

Genericな「New High Breakout」は独立カテゴリにせず、上記Setupの確認要素として扱う。

### Setup Type と Lifecycle

同じ分類軸に混ぜない。

- `setup_type`: どのチャート型から始まったか。ブレイク後も原則不変。
- `lifecycle`: 現在どの状態にあるか。価格構造に応じて更新。

Lifecycleの正規値:

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
```

遷移の基本形:

```text
SETUP
  ↓ Pivot突破
BREAKOUT
  ├─→ EXTENDED
  ├─→ PULLBACK
  ├─→ RETEST
  ├─→ 3WT
  ├─→ TIGHT
  ├─→ ASCENDING_BASE
  └─→ FAILED_BREAKOUT
```

`FAILED_BREAKOUT` 後に新しい有効Baseを形成した場合は、新しいSetupとして `SETUP` へ戻す。元のブレイクを成功扱いに書き換えない。

### Step 1 — 一次スクリーナー

TradingView標準 Stock Screener を使用し、週1回を基本に手動更新する。

目的は、Stage 2候補を**広めに**抽出し、後段の母集団を作ること。一次段階でSetup形状を判定しない。

#### US

- Price > SMA50
- Price > SMA200
- SMA50 > SMA200
- Performance 3M > 0%
- Performance 6M > 0%
- 現在値が52週高値から30%以内
- 平均売買代金の目安: 10M USD/日以上

格納先: `🇺🇸一次スクリーナー`

#### Japan

- Price > SMA50
- Price > SMA200
- SMA50 > SMA200
- Performance 3M > 0%
- Performance 6M > 0%
- 現在値が52週高値から30%以内
- 平均売買代金の目安: 500M JPY/日以上

格納先: `🇯🇵一次スクリーナー`

一次スクリーナーでは取りこぼし回避を優先する。150SMA、200SMA傾き、52週安値からの上昇率、RS、ベース構造は後段で確認する。

### Step 2 — Stage 2 / Pre-Setup定量確認

一次リストをTradingView MCP経由で読み、日足OHLCVを取得して後段判定を行う。

Stage 2確認の基本項目:

- Price > SMA50
- Price > SMA150
- Price > SMA200
- SMA50 > SMA150 > SMA200
- SMA200が上向き
- 52週安値から十分上方
- 52週高値から大きく離れすぎていない

ただし、ここでもHard Filterを増やしすぎない。

### Step 3 — Pre-Setup抽出

固定60日レンジのBase DepthをHard Filterにしない。

優先して見る項目:

- 直近20日程度の高値 / 抵抗帯までの距離
- 直近10〜15日の値幅収縮
- ATR収縮
- 出来高Dry-up
- 高値・安値の切り上げ
- ベース期間と形状
- 明確なPivot候補の存在
- ベンチマークに対するRelative Strength

Pre-Setupはパターン確定前の監視リストであり、VCP / CWH / Base Breakoutの分類は必須ではない。

格納先:

- `🇺🇸プレセットアップ`
- `🇯🇵プレセットアップ`

区分:

- **Ready**: Pivot候補まで概ね3%以内
- **Near**: Pivot候補まで概ね3〜7%
- **Forming**: それ以上でも、収縮・出来高低下・右側形成等が進行している

既に明確にPivotを突破した銘柄はPre-SetupではなくBreakout側で扱う。

### Step 4 — チャート判断

Pre-Setup候補をチャートで確認し、次のいずれかに分類する。

- VCP
- CWH
- Base Breakout
- 不採用 / 再形成待ち

確認順序:

```text
Setup構造
→ Standard Pivot
→ 必要なら Early Entry / Cheat Entry
→ 構造的Stop
→ Entry-to-Stop Risk
→ Extended判定
```

### Step 5 — 正式Setup

正式にエントリー監視する銘柄だけSetupリストへ昇格する。

- `🇺🇸セットアップ`
- `🇯🇵セットアップ`

Setupリストは **setup_type軸** で管理する。

- VCP
- CWH
- Base Breakout
- 無効 / 再形成待ち

有効な正式Setupは原則 `lifecycle=SETUP` とする。

### Step 6 — Pivot突破後 / Post-Breakout

Pivotを明確に突破したら、元の `setup_type` を保持したまま `lifecycle=BREAKOUT` へ移行する。

TradingView格納先:

- US: `❤️ブレイクアウト`
- Japan: `💙ブレイクアウト`

TradingViewのブレイクアウトリストは **lifecycle軸** で分類する。

1. **BREAKOUT** — Pivot突破直後。出来高・終値・Gap・Riskを確認
2. **EXTENDED** — Pivotから上昇しすぎ。新規で追わず待つ
3. **PULLBACK** — 10EMA / 21EMA等への押し。支持と売り圧力低下を確認
4. **RETEST** — 元Pivot近辺の再テスト。Pivotが支持へ転換するか確認
5. **3WT** — Three Weeks Tight。ブレイク後の追加買い候補
6. **TIGHT** — 高値圏で値幅収縮。次のContinuation Entry候補
7. **ASCENDING_BASE** — 上昇トレンド中に新Baseを形成
8. **FAILED_BREAKOUT** — 元Pivot・主要支持を明確に割りブレイク仮説が崩れた状態

重要: `PULLBACK / RETEST / 3WT / TIGHT / ASCENDING_BASE` は元のSetup Typeを置き換えない。例: VCPからブレイクした銘柄がRetest中なら `setup_type=VCP`, `lifecycle=RETEST`。

過去snapshotに元のsetup_typeが保存されていない場合は、後から推測で補完しない。UIでは未判定として表示する。

---

## 3. Pivot / Entryの定義

### Standard Pivot

ベースの正式なブレイクポイント。

- VCP: 最終収縮の高値 / 明確な抵抗帯
- CWH: Handle高値
- Base Breakout: ベース上限・抵抗帯

### Early Entry

Standard Pivot前に、右側の短期抵抗・小さな高値を抜くエントリー。

### Cheat Entry

Early Entryよりさらに早い、非常にタイトなMini-consolidation / micro-VCP / trendline break等を使う攻撃的エントリー。

---

## 4. Pivotアラート運用

Pre-Setupへ追加する際は、Pivot候補を決めてTradingView価格アラートを設定する。

アラート名:

```text
REVIEW | TICKER | Pivot PRICE
```

条件:

- `Price > Pivot`
- 1分判定を基本
- 初回発火で自動停止
- Mobile Push: ON
- Popup: ON

**REVIEWアラート発火 = 自動Buyではない。**

発火後に次を再確認する。

- Setupが崩れていないか
- 出来高
- Gap幅
- Pivotからの乖離
- Stop位置
- Entry-to-Stop Risk
- 市場環境

条件を満たした場合のみ正式Setup / Entry候補として扱う。

Pivotがベース再形成で変化した場合、古いアラートは削除して新しいPivotで再作成する。

---

## 5. RSの扱い

RSIとは分離する。

### RS Line

```text
Stock Price / Benchmark Price
```

- US benchmark: S&P 500系
- Japan benchmark: TOPIX

### RS Rank proxy

現行の独自proxy:

```text
RS_score = 0.4 × R_3M
         + 0.2 × R_6M
         + 0.2 × R_9M
         + 0.2 × R_12M
```

各Rは株価リターン − benchmarkリターンを基本とし、対象Universe内でpercentile化する。

これはIBD RS Ratingそのものではないため、名称は **RS Rank** とする。

---

## 6. Position sizingの基本

基本式:

```text
Position Size = 許容口座リスク / Entry-to-Stop %
```

初期目安:

- 1 trade risk: 0.75〜1.0%
- 上限目安: 1.25%
- 1銘柄の最終Position上限目安: 20%

Cheat → Early → Standardで増し玉する場合は、勝ちポジションにのみ追加する。平均単価を下げるためのナンピンは行わない。

---

## 7. 定期運用

### Weekly

1. TradingView標準Stock ScreenerをUS / Japanで実行
2. 一次スクリーナーWatchlistを更新
3. Pre-Setup候補を再抽出
4. Pivotとアラートを更新
5. 既存Setupの昇格 / 降格を整理
6. Breakout銘柄のLifecycleを再判定

### Daily

- Pre-Setup / Setupの価格構造変化を確認
- 発火済みREVIEWアラートを再評価
- Breakout銘柄を `BREAKOUT / EXTENDED / PULLBACK / RETEST / 3WT / TIGHT / ASCENDING_BASE / FAILED_BREAKOUT` へ更新
- Market Outlook / Distribution Days / Momentum Healthを更新可能な範囲で確認

---

## 8. 実装上の制約

- TradingView MCP `run_screener` は429が発生することがあり、全市場スクリーニングの自動運用には現状依存しない。
- Watchlist読書き、個別OHLCV取得、単純価格アラートはMCPで利用する。
- Pine Screenerは現行の標準運用には使用しない。
- Pattern判定は完全自動検出ではなく、定量候補抽出 + チャート確認を基本とする。
- 過去の保存データは遡及上書きせず、legacy `setup` しかないsnapshotはUI互換層で表示する。


## 9. Pre-Setup抽出エンジン v1

`config/pre-setup.json` / `scripts/build_pre_setup.py` を追加。一次リストの保存時点を評価日以前に限定し、未来の足・現在のUniverseを過去評価へ混ぜない。未取得銘柄も除外理由として保存し、取得済みだけを全母集団として扱わない。

- 必要日足65本。未確定足は既存の市場別処理で除外。
- Pivot候補は当日を除く20営業日高値。0.75%以内の接触が2回以上で抵抗帯の明確さを確認。
- 直近10日/前10日の値幅比0.85以下、True Range平均比0.90以下、直近10日/前50日の出来高平均比0.80以下のうち2条件以上。
- 終値が上向き50DMAより上、Pivotまで15%以内を候補条件とする。
- 候補条件を満たした後に、距離3%以内Ready、3%超7%以内Near、7%超15%以内Forming。
- 当日高値がPivot候補に到達・通過した場合はPre-Setupから除外して再確認。終値突破はBREAKOUT、日中のみ通過は状態未判定。
- 長期Stage 2補助項目と高値・安値構造も保存する。欠損はnull。固定60日Base DepthはHard Filterにしない。
- `setup_type`は未確定のためnull、正式確認はfalse。候補は`lifecycle=SETUP`とし、readinessを別に保存する。Entry/Stopはあくまで候補水準。

これらは独自の初期閾値で、収益性や投資判断の有効性の検証ではない。VCP/CWH/正式Pivotの確定と昇格はチャート確認を必要とする。

入力Universe形式:

```json
{"asOf":"YYYY-MM-DD","markets":{"US":{"name":"🇺🇸一次スクリーナー","symbols":["NASDAQ:...","NYSE:..."]},"JP":{"name":"🇯🇵一次スクリーナー","symbols":["TSE:..."]}}}
```

実行:

```bash
python scripts/build_pre_setup.py --input observations/YYYY-MM-DD/ohlcv.json --universe observations/YYYY-MM-DD/primary-universe.json --as-of YYYY-MM-DD
python tests/test_pre_setup.py
```

評価結果を `data/pre-setup/<rule version>/<asOf>.json` に追記し、`data/pre-setup/latest.json` に登録する。過去の異内容上書きは拒否する。現時点では、全一次銘柄の確定足収集・定期実行・この新しい評価の画面接続は未実装。既存テーマ由来のSetup候補を、この一次リスト評価として表示しない。

## 10. Lifecycle表示の判定と欠損

共通判定は `lib/setup-state.mjs`。保存済みlifecycleを最優先し、未保存の場合のみ有効な価格・EntryからSETUP/BREAKOUT/EXTENDEDを推定する。価格がEntry未満ならSETUP。欠損や0を価格として扱わず未判定にする。旧Pullback/Retestの元型・元Pivotは推測で埋めない。

OverviewはSetup Type、Lifecycle、Entry判定、形成度を分離し、保存状態/推定/未判定を明記する。Entry候補フィルタとLifecycleフィルタは併用でき、URLで保存する。分析ダイアログもFORMING等の元ステータスを残したままLifecycleを補足する。

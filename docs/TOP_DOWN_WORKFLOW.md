# Top-Down Trading Workflow

## 目的

Theme Atlasの既存データモデルを使い、個別チャートから逆算するのではなく、上位レイヤーから順に候補を絞る。

```text
Market
  ↓
Theme
  ↓
Industry / Peer Group
  ↓
Stock Leader
  ↓
Setup
  ↓
Pivot / Entry
```

このフローは自動売買ロジックではない。各レイヤーは候補の優先順位または行動制約を与え、最終Entryは保存済みのSetup/Lifecycle、Entry、Stop、Risk、チャート確認を使って判断する。

## 1. Market Gate

市場環境は `lib/market-action.mjs` の保存済みMarket Outlookを使う。

- `CONFIRMED_UPTREND`: 個別Entry条件を確認
- `UPTREND_UNDER_PRESSURE`: 候補を絞り慎重に確認
- `MARKET_IN_CORRECTION`: 新規Entryは待機
- `UNASSESSED`: 市場判定が整うまで確認優先

重要: Market GateはTheme/Stockの技術ランキングを削除・書き換えない。例えばCorrectionでも強いThemeや形成中Setupは監視対象として残し、実行行動だけを `WAIT` にする。

`automaticBuy` は常に `false`。

## 2. Theme

新しい隠れスコアは作らず、既存の保存済みTheme評価を再利用する。

Top-Down候補は `technicalThemeCandidate()` の条件を使う。

- Daily評価が存在
- Weekly Strengthが設定閾値以上
- Ready Setupが存在
- Theme全体がExtendedではない
- 短期Strength/Breadthの同時悪化に該当しない

Themeの定量ロジックや閾値を変更する場合はTop-Down表示だけで変更せず、既存のversioned scoring rulesを更新する。

## 3. Industry / Peer Group

### 現状

現行Observed snapshotには独立したIndustry / Peer Groupフィールドがない。

そのため初期実装では以下を禁止する。

- Theme名からIndustryを推測する
- Ticker名や企業名からPeer Groupを推測する
- AI文章から分類を生成して確定データとして表示する

フィールドが存在する場合だけ、次の順に読み取る。

1. `quantitative.peerGroup`
2. `quantitative.industry`
3. `quantitative.industryGroup`

未取得なら `未接続` / `—` とする。

### 将来

Industry / Peer Groupを正式接続する場合は、US/JPそれぞれの分類ソース、評価日、分類version、履歴保存、分類変更時の扱いを決める。過去snapshotへ現在の分類を遡及適用しない。

## 4. Stock Leader

候補Theme内で既存Leader Score順に並べる。

初期Top-Down shortlistでは次を優先する。

- Theme内 Top 3
- Stage 2
- Leader Score上位

Leader Scoreの構成要素は既存versioned scoring rulesを正とする。Top-Down専用に別のLeader Scoreを作らない。

同一銘柄が複数Themeに属する場合はThemeごとの関係を保持する。

## 5. Setup

Setup TypeとPost-Breakout Lifecycleは別軸のまま維持する。

### Setup Type

正式な起点Setupは次の3種類。

- VCP
- CWH
- Base Breakout

### Lifecycle

- SETUP
- BREAKOUT
- EXTENDED
- PULLBACK
- RETEST
- 3WT
- TIGHT
- ASCENDING_BASE
- FAILED_BREAKOUT
- UNASSESSED

Top-Down表示は保存済みLifecycleを優先し、自動候補は確定状態を上書きしない。

## 6. Pivot / Entry

最終レイヤーでは次を別々に表示する。

- Pivot
- Entry
- Stop
- Entry-to-Stop Risk
- Lifecycle
- Technical Candidate / Watch / Extended

重要: Pivotが未保存の場合、EntryをPivotとして代用しない。

Entry候補は既存と同じく、概ね次のAND条件で扱う。

```text
Technical Theme Candidate
× Stage 2
× Ready
× Valid Entry / Stop
× Not Extended
```

REVIEW alertの作成・発火・再設定は別Issueで管理し、Top-Down表示だけでTradingView alertを変更しない。

## UI

US / Japan OverviewのMarket Outlookより前に `00 TOP-DOWN DECISION PATH` を追加する。

表示内容:

1. Market Gateと参考投資比率
2. Theme候補数
3. Industry / Peer接続状態
4. Leader銘柄数
5. Setup銘柄数
6. Pivot / Entry候補数
7. Top-Down shortlist

既存01〜09セクションは根拠確認用としてそのまま残す。Top-Downはそれらの上に置く意思決定導線で、既存データを複製しない。

## 保存・履歴ルール

- 過去snapshotを書き換えない
- 最新Industry分類を過去へ遡及joinしない
- Setup/Lifecycleはdated registryを正とする
- 欠損値を0点や推測値で補完しない
- Market stateとTheme/Stock technical scoreを一つの点数へ混ぜない

## 現在の未接続

- Industry / Peer Groupの正式データ源
- 本番UniverseのRS Rank proxy
- 全一次Universeの最新OHLCV安定取得
- EPS / Revenue等のFundamental補助評価
- Pivot REVIEW alert同期
- 新テーマ発見・出典付きInstitutional Focus

これらを接続しても、Top-Downのレイヤー順序とpoint-in-time原則は維持する。

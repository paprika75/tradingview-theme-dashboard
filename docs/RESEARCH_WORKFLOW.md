# 日付付き研究記録と市場行動条件

## 公開する対象

一次 / Pre-Setup / 正式Setup / Breakoutの名前付き8リストと、既存の公開Themeカタログを対象にする。TradingViewの他リストや個人ポジションを取り込まない。銘柄が対象から外れても保存済みログは保持する。

`observations/2026-10-08/research-universe.json` は現在取得した研究リストの記録。`observedAt` は受領後の記録時刻、`modifiedAt` はTradingView側の変更時刻であり、過去のUniverseの取得時刻ではない。過去日へ遡ってこのメンバーを使わない。

## 正式Setupの確認と保存（Issue #2）

1. `scripts/propose_setup_review.py --input <proposal-input.json>` で候補水準を算出する。
2. チャート確認者が構造窓を指定する。`completedBars` は確定済み足だけ、`pivotWindow` / `stopWindow` は `start`, `end`, `basis` を持つ。VCPは最終収縮、CWHはHandle、Base BreakoutはBaseの抵抗帯・支持帯を指定する。
3. Pivotは選択窓の高値、Stopは支持窓の安値。EntryはPivot＋任意buffer（既定0.1%）、Riskは `(Entry−Stop)/Entry`。乖離10%以上はExtended候補。これらは構造窓を手動指定した定量候補で、チャート型の確定ではない。
4. `docs/SETUP_JOURNEY.md` の構造を手動確認し、`setupConfirmed` / `lifecycleConfirmed` / 各pattern checkを確認した記録を作る。元Pivot・episode・Lifecycle別Entry Planと出典を記録する。
5. 提出ファイルは `asOf`, timezone付き`reviewedAt`, `reviewer`, `changeReason`, `symbols` のパッチ形式。`symbols` の各値に `market` を含める。
6. `python scripts/validate_setup_reviews.py --input <review.json>` で事前確認、`python scripts/save_setup_review.py --input <review.json>` で保存する。

保存処理は既存銘柄の状態を保持した完全Registryを新日付へ追加し、manifestを更新する。未確認案、`RULE_CANDIDATE`を確認済みとした記録、未来Pivot、無効Stop、同episodeの元Pivot変更を拒否する。同日同内容は再実行可、同日異内容は拒否し、次の評価日の記録にする。後日Registryがある状態での過去挿入も拒否する。

正式Setupの無効化は手動確認した `FAILED_BREAKOUT` を保存し、Entryを無効にする。以後の新Baseは新episodeにして前episodeへリンクする。Pre-Setupの不採用候補は正式昇格しない。候補算出・保存CLIはTradingViewへ書き込まない。

実銘柄の手動構造確認は未実施。旧Registryの移行記録に架空のチャート確認や水準を追加しない。

## 銘柄分析履歴（Issue #10）

```bash
python scripts/build_stock_analysis.py \
  --universe observations/2026-10-08/research-universe.json \
  --generated-at <実際の生成時刻・timezone付き> \
  --change-reason <変更理由>
```

- 生成時刻以前に保存されたObservedの確定技術評価を使用。最新市場データを取得できない場合は `OLDER_INPUT` とデータ日を明記する。
- この新しい研究評価には現在のdated Registryを参照できるが、元のObserved snapshotへ書き戻さない。市場データ日と研究評価日を別々に保存する。
- 技術メモは `TECHNICAL_MODEL`。手動チャート確認を実施したようには扱わず、元SetupのEntry/Stopを継続型へコピーしない。
- 取得できない銘柄はmanifestで `UNANALYZED` / 理由を保存し、価格・Pivot・Riskを生成しない。
- 分析日、生成時刻、市場データ日、sourceのsnapshot path / timestamp / Registry日、版、変更理由、内容hashのIDを保存。
- `data/stock-analysis/logs/<研究評価日>/<hash>.json` は40銘柄単位の変更不可ログ。manifestだけ更新する。同日再分析は異なる生成時刻・IDで追記し、旧版を保持する。
- 保存失敗・未来Universe・未来生成時刻でmanifestを進めない。生成日を過去へ戻すことも拒否する。
- Legacy VSTファイルは改変せず、readerが旧ログと新ログを合わせて読む。

銘柄ダイアログの通常表示は、選択日の終了（JST）までに生成された分析だけ。入力足が古くても生成が後日なら表示しない。「最新分析を別表示」を押した場合だけ最新へ切り替える。DemoではObserved分析を表示しない。

Setupセクションの「最新の監視銘柄一覧・分析を別表示」は現在の対象と収集状況を確認する独立表示。監視リストの日付を示し、過去の市場評価日のメンバーとして扱わない。

今回の対象791銘柄中、212銘柄に保存済み技術データのメモを生成。残る579銘柄は未分析。従来のVST手動メモは別に保持。OHLCVの接続エラーが解消するまで全対象の新しい価格評価は完了扱いにしない。

## Market Outlookから行動条件へ（Issue #11）

| Market Outlook | 行動条件 | 候補の扱い |
|---|---|---|
| Market in Correction | WAIT | 技術候補を監視。指数回復・FTD待ち |
| Uptrend Under Pressure | LIMIT | 絞った候補について支持・出来高・Stop・比率を慎重に確認 |
| Confirmed Uptrend | CHECK_ENTRY | Lifecycle別のEntry・Stop・Risk・直近構造を確認 |
| UNASSESSED | VERIFY | 市場判定を補完。価格上昇だけで新規Entry可としない |
| 更新予定を過ぎたデータ / 不整合 | VERIFY | 最新の市場と個別構造へ更新して再確認 |

どの状態も自動Buyの許可ではない。日本の指数出来高が不足している場合は価格トレンドと出来高未判定を分ける。UNASSESSEDへ比率0%や安全判定を割り当てない。

3本柱、New Entry、Leader / Setupには市場条件を除いた技術候補を使い、市場行動条件を別表示する。各セクションには同じ評価日・版の行動条件を共通表示。既存のテーマ点数 / Momentum Health gate / Opportunity Scoreは比較用に残すが、従来Scoreや技術候補数を新規Entryの許可として扱わない。

`scripts/build_market_action.py` が既存Outlook / 比率から `1.0.0-market-action` を保存する。既存の指数評価・比率閾値・Themeの計算は変更しない。これは保存済み評価の決定的な再表示で、当時公開済みの許可を意味しない。新Outlook / exposureを生成した後に再実行する。評価日・入力版・状態・比率の不整合はDashboardでVERIFYにする。

# Pre-Setup → Formal Setup → Post-Breakout / Entry Plan v1

既存の `docs/SETUP_STATE.md` とPoint-in-time Registryに追加するモデル。Setup Type / Lifecycleを再定義しない。市場評価・Market Outlook・参考投資比率・Theme/Leader重み・Lifecycle候補の閾値は変更しない。

## 実装と境界

- `scripts/setup_journey.py`: 確認状態・昇格要件・Lifecycle別水準・再形成履歴の読み取りモデル。
- `scripts/validate_setup_reviews.py`: 明示的なチャート確認記録の検証。ファイル保存・Watchlist移動・Alert操作は行わない。
- `scripts/build_live_with_setup_state.py`: 通常入口を維持。**新しい**Observed評価は `3.3.0-setup-journey-v1` で保存する。
- Overviewの08 SETUPS内にPre-SetupとEntry Planを追加。8セクションの構成を維持。
- 一次リストの実データ収集、実際のチャート確認記録・新規Observed生成は別作業。空のmanifestは未保存を示し、候補が0件と判断した意味ではない。
- この版は読み取り接続。公開ページからGitHub Registryを書き換える昇格ボタンは設けない。

## 1. 独立した軸

| 軸 | 意味 | 自動更新で確定するか |
|---|---|---|
| `setup_type` | 起点のVCP / CWH / Base Breakout | しない |
| `lifecycle` + `lifecycleConfirmed` | 保存した現在状態と確認の有無 | 手動確認を上書きしない |
| `lifecycleCandidate` | OHLCV候補 | 確定状態・Watchlist移動に採用しない |
| `setupJourney.phase` | Pre-Setup / Formal Setup / Post-Breakout / 再形成待ち / 未確認 | 確認フラグを参照 |
| `preSetup.readiness` | Ready / Near / Forming | 候補形成度のみ |
| `entryPlan` | 現在Lifecycleに対応する独立した水準案 | 確認記録が必要 |

既存3.2の互換仕様では、Registryがないと `lifecycle` にも候補を保存する場合がある。**`lifecycle` の文字列だけを確定状態と扱わない。** 新モデルは `lifecycleConfirmed=true`、非RULE_CANDIDATEのsource、評価日以前のRegistryと一致する状態だけを確認済みとする。移行BREAKOUT (`lifecycleConfirmed=false`) は未確認のまま。

## 2. 状態遷移と昇格要件

| 現在 | 次 | 必須確認 |
|---|---|---|
| Pre-Setup (Ready / Near / Forming) | Formal Setup | 型・構造・正式Pivot・Standard Entry・構造的Stopをチャート確認し、Registryへ保存 |
| Formal Setup / SETUP | Post-Breakout / BREAKOUT | Pivot突破と現在状態を明示的に確認。元型・元Pivot・episodeを保持 |
| Post-Breakout | 他のPost-Breakout Lifecycle | 現在状態を確認し、対応する新しいEntry Planを別途保存 |
| FAILED_BREAKOUT | 再形成待ち | 旧Entryを無効化。失敗状態はその日の評価に残す |
| 再形成待ち / 新Base形成 | 新しいFormal Setup | **新episodeId**、previousEpisodeId、型・Pivot・Stopを再確認 |
| 未確認 / 候補が保存状態と不一致 | 再確認 | 状態・水準の採用を保留。自動でWatchlistを移動しない |

Readyという距離分類だけでは昇格しない。REVIEW alert発火も昇格やBuyではない。

手動構造チェックは次を明示する（価格による完全自動パターン確定ではない）。

| 型 | `patternChecks` の必要項目 |
|---|---|
| VCP | contractionsDecreasing / volumeDryUp / finalContractionClear |
| CWH | cupStructure / handleStructure / handleResistanceClear |
| Base Breakout | baseStructure / resistanceClear / rightSideStructure |

VCPでは収縮の連続性・最終収縮、CWHではカップとハンドルの構造、Baseではベースと抵抗帯・右側をチャートで確認する。適切な期間や深さの定量条件は今後の拡張であり、現段階ではcheckboxを自動判定しない。

## 3. Registryへの追加フィールド

既存schemaVersion 1と手動Setup Type / Lifecycleを保持し、銘柄ごとに次を任意追加する。

```json
{
  "setup_type": "VCP",
  "setupConfirmed": true,
  "setupTypeSource": "CHART_REVIEW",
  "lifecycle": "SETUP",
  "lifecycleConfirmed": true,
  "lifecycleSource": "CHART_REVIEW",
  "setupReview": {
    "episodeId": "NASDAQ:EXAMPLE:2026-10-08:1",
    "previousEpisodeId": null,
    "setup_type": "VCP",
    "reviewedAsOf": "2026-10-08",
    "patternChecks": {
      "contractionsDecreasing": true,
      "volumeDryUp": true,
      "finalContractionClear": true
    },
    "originPivot": {
      "id": "origin-1", "price": 100, "confirmed": true,
      "asOf": "2026-10-08", "source": "CHART_REVIEW"
    }
  },
  "entryPlans": [{
    "id": "standard-1", "episodeId": "NASDAQ:EXAMPLE:2026-10-08:1",
    "originPivotId": "origin-1", "lifecycle": "SETUP", "kind": "STANDARD",
    "pivot": {"id": "origin-1", "price": 100, "confirmed": true,
              "asOf": "2026-10-08", "source": "CHART_REVIEW"},
    "entry": 100.1, "stop": 96,
    "stopBasis": "最終収縮の安値", "trigger": "抵抗帯を突破して再確認",
    "invalidation": "構造的支持を割る", "confirmed": true,
    "asOf": "2026-10-08", "source": "CHART_REVIEW"
  }]
}
```

上記は**架空のスキーマ例**。実銘柄の確認や価格を生成したものではない。

- originPivotは同episode内で不変。Continuation用 `entryPlans[].pivot` は新しい支持・抵抗帯を持てる。
- episode / originPivotId / lifecycleが違う旧案はOBSOLETE。旧案を削除せず保存評価で追跡する。
- Standard案は正式Pivotに対応することを必要とする。Early / CheatをStandardの代替として昇格に使わない。
- Entry / Stopをq.entry / q.stopからコピーしない。元型不明のLegacyは推測補完しない。
- 確認日はRegistry日以前、Registryは評価日以前。将来の案は参考表示にも混ぜない。
- `setupReview`がない旧Registryでも確認済み型・状態は維持するが、正式Pivot / 水準案は未保存とする。

確認後の保存前に実行する。

```bash
python scripts/validate_setup_reviews.py --input /path/to/proposed-registry.json
```

検証後は新しい日付のRegistryファイルへ保存しmanifestへ登録する。同日異内容や既存評価の上書きは行わない。自動検証が成功してもTradingView移動はチャート確認を行った運用者が別途実施する。

## 4. LifecycleごとのEntry / Stop / Risk

| Lifecycle | `kind` | Entryの意味 | Stopの意味 | 水準未確認時の次の確認 |
|---|---|---|---|---|
| SETUP | STANDARD / EARLY / CHEAT | 正式Pivot / 右側短期抵抗 / micro構造の各トリガー | 各案の構造的支持。案同士で別に保存 | 型・Pivot・支持・乖離 |
| BREAKOUT | BREAKOUT | 確認した突破価格・トリガー | initial stop | 出来高・Gap・終値・初期支持 |
| EXTENDED | なし | **有効な新規Entryなし** | 新規Entry案として表示しない | 押し・再テスト・新しい収縮待ち |
| PULLBACK | CONTINUATION | 21EMA等の支持から反発するトリガー | 今回の押し安値・支持割れ | 支持・売り圧力低下 |
| RETEST | REENTRY | 元Pivotの支持を確認した再Entry | 今回の再テスト安値 | Pivot支持転換 |
| 3WT / TIGHT | ADD_ON / CONTINUATION | 最新の収縮上限・継続Pivot | 継続型の支持 | 収縮構造・継続突破 |
| ASCENDING_BASE | NEW_PIVOT | **新しいBaseのPivot** | 最新Baseの構造的支持 | 新Baseの構造 |
| FAILED_BREAKOUT | なし | **Entry無効** | 旧案は新規Entryに採用しない | 新episodeで再形成 |
| UNASSESSED | なし | 未判定 | 未判定 | 確認記録・材料不足 |

`riskPct = 100 × (Entry − Stop) / Entry`。正の有限価格かつStop < Entryの場合のみ計算。欠損・0・Stop≥Entryではnull。これは予定水準間の距離であり、保有損益・口座リスク・株数ではない。各案にRiskを持たせ、Early / Cheat / Standardで単一のStopやRiskを共有しない。

`entryPlan.status` は CONFIRMED / REVIEW_REQUIRED / WAIT / INVALID。個別案は CONFIRMED / PROPOSED / OBSOLETE / INVALID。候補と保存状態が不一致、価格が欠損・評価日より古い場合は案の採用を保留。状態・候補は残す。

## 5. Observed / Dashboardの接続

新しいsnapshotには `stock.quantitative.setupJourney` と市場単位の `setupJourneys` を保存。市場配列に一次リストのテーマ外銘柄やRegistry銘柄も含め、Theme Leaderへの所属を正式昇格の前提にしない。

Pre-Setupは `data/pre-setup/latest.json` の評価日以前の保存ファイルだけを読む。過去評価なら保存日・版・再抽出待ちを明示し、その距離だけを理由に現在のPre-Setup扱いにしない。UIは新しいRegistryを過去Observedへlive joinせず、保存されたjourneyだけを表示する。

チャート確認したoriginPivotがある場合に限り、Lifecycle候補のPivot基準にそれを使う（閾値・優先順位は既存v1のまま）。直近ローリング高値の旧q.entryを元Pivotと誤認しない。`lifecycleCandidatePivot` に基準を保存。ない場合は既存の候補ロジックを維持し、確認済み水準へ昇格させない。

Overview上表のLegacy Entry / Stop / Riskは**元Setupの参考値**と明記し、Lifecycle別Entry Planとは区別する。既存テーマのスコア・フィルタ用技術条件は変更しない。

## 6. 続く作業

1. #1: 全一次銘柄の確定OHLCV収集と実データでの抽出確認。
2. #2 / #6: 実際のチャート確認を新しいRegistryに保存し、新規Observedへ反映。型の定量補助と昇格/降格の運用を拡張。
3. #3 / #6: REVIEW alertのid・Pivot版・active/fired/obsolete・イベント日付を別履歴で保存。候補や発火を自動Buyにしない。今回はalert同期を実装していない。
4. Theme Leaderとの関係、#10の分析履歴・評価時点、#11の市場判断接続。今回はロジックを変更しない。


日付付きRegistry保存、構造窓による水準候補、分析履歴と市場行動条件の実装は [RESEARCH_WORKFLOW.md](RESEARCH_WORKFLOW.md) を参照。実銘柄の全OHLCV取得と手動チャート確認は引き続き必要。

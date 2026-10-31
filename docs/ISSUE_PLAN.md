# Issue Plan — 2026-11-01

監査対象main: `46eea9b80a8d1f60c7c9ecad84d5acf16763d7e5`（PR #15 squash）。open Issue全11件とclosed #9/#11、PR #15のreview、README/Workflow/Setup/Research/Top-Down仕様・実コードを照合した。

## 優先度

P0: 実運用の入力鮮度・確認済み水準の意味に関わる基盤。P1: 次の機能/安定性・検証。P2: 補助評価・拡張。優先度だけで依存を無視せず、小さな独立不具合 #16 を最初に修正する。

| Issue | 優先度 | 未完範囲 | 依存/先行可能部分 |
|---|---|---|---|
| [#5](https://github.com/paprika75/tradingview-theme-dashboard/issues/5) | P0 | 入力・更新・分析coverageの運用統合 | 入力元/利用条件確認。契約設計は先行可 |
| [#6](https://github.com/paprika75/tradingview-theme-dashboard/issues/6) | P0 | Top-DownのLeader集合・確認済みLifecycle Entry Plan整合 | 保存fixtureで先行、実銘柄受入は#2/#5 |
| [#16](https://github.com/paprika75/tradingview-theme-dashboard/issues/16) | P1 | Top-Down取得失敗時の無限再試行抑止 | 独立、最初に着手 |
| [#14](https://github.com/paprika75/tradingview-theme-dashboard/issues/14) | P1 | Industry/Peer分類の契約・時点保存・UI | schemaは先行、収集境界は#5 |
| [#1](https://github.com/paprika75/tradingview-theme-dashboard/issues/1) | P1 | 実Pre-Setup検証・市場別流動性 | 実入力#5。本番RS#4は初回の必須条件にしない |
| [#2](https://github.com/paprika75/tradingview-theme-dashboard/issues/2) | P1 | 実チャート確認→新Registry→新Observedの運用受入 | #1/#5、表示確認#6 |
| [#3](https://github.com/paprika75/tradingview-theme-dashboard/issues/3) | P1 | REVIEW状態モデル・同期・旧Pivot無効化 | schema先行、同期は#2/#5のPivot/episode境界 |
| [#4](https://github.com/paprika75/tradingview-theme-dashboard/issues/4) | P1 | RS式/field/benchmark/本番Universe | 入力#5。定義は先行可 |
| [#7](https://github.com/paprika75/tradingview-theme-dashboard/issues/7) | P1 | JP指数出来高の入力仕様 | 独立調査→#5、US等の全面blockerにしない |
| [#8](https://github.com/paprika75/tradingview-theme-dashboard/issues/8) | P2 | EPS/売上の補助評価 | #5の入力、業種差は#14 |
| [#12](https://github.com/paprika75/tradingview-theme-dashboard/issues/12) | P2 | 出典付き材料→テーマ候補 | #5の採用フロー、分類は#14を参照 |
| [#17](https://github.com/paprika75/tradingview-theme-dashboard/issues/17) | P2 | Peer内RS/Leadership比較 | #14 + #4 |

## 統合・完了・分割

- #10: 履歴生成・不変ログ・時点別readerはmainで実装済みとしてcompletedで閉鎖。新OHLCV取得/coverage/既存分析生成は #5 へ移管。全銘柄の分析完了とは扱わない。
- #1/#2/#6に重複した収集・更新を #5 に一本化。#1は抽出/流動性、#2は実チャート確認と受入に限定。
- #6のalert data未完は #3 に集約。#11は完了維持。#9も再openしない。
- #14からPeer内比較を #17 に分割。#14は分類の最小接続だけで閉じられる。
- PR #15のstaging/cache reviewは修正済み。catchのsignature欠落による無限再試行は未修正のため #16 新設。
- #6/#14は統合しない。#6はTheme→Leader→Setup→確認済み水準の整合、#14は独立Industry/Peer分類。相互に全完了待ちを作らない。

## 今すぐ着手する5件と順序

1. #16: 失敗時の要求回数を有界にする独立修正。
2. #6: 既存JourneyモデルをTop-Downに接続し、技術候補と採用水準を区別。
3. #5: dated入力契約と失敗復旧を固定し、既存build/分析CLIを運用として接続。
4. #14: source/日時/version付き分類schema・保存・readerを接続。
5. #1: 入力が揃った日米の実Pre評価と流動性を検証。

#5の入力待ち中に#14の契約設計は進められる。#1後は #2の手動確認受入 → #3の同期。#4/#7は入力仕様の独立作業として進め、#17は#14+#4の後。#8/#12はその後。

## README/docsとのズレ

- READMEの判断経路にIndustry/Peerがなく、PR #15と不一致 → 経路・完了表示・優先順を更新。
- 「Lifecycle別モデル未実装」と「実銘柄未検証」が混在 → モデル完成と#2の運用受入、#6の画面整合を分離。
- #10冒頭の「VSTのみ/常に最新」は実装前の記述 → 完了基盤を明記して閉鎖。
- Workflowのalert削除一律方針 → #3で旧alert無効化/停止・履歴保持を設計する方針へ整理。
- RSの差分式/倍率式、rsLineの意味、JP長期benchmarkの不一致 → #4を正規の未完として明示。今回計算は変更しない。
- 過去のWebSocket障害を現在の恒久障害と断定しない。現在の疎通はこの監査では未検証。
- CHANGELOGの日付付き「当時未完」は歴史記録として保持し、現状は本書/各Issueを参照する。

Marketは技術候補を消さず行動制約、Setup Type/Lifecycle分離、候補から自動確定しない、過去snapshotは不変、分類推測禁止を全Issueで維持する。
非公開化/Vercel移行は保留。今回の作業はIssue・文書整理のみで、データ収集・市場/Theme評価・スコア・過去snapshot・公開設定を変更しない。

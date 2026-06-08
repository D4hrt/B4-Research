# 参加型LLMマルチエージェントシミュレーション環境

**Design and Implementation of a Participatory LLM Multi-Agent Simulation Environment**

岡山大学 工学部 情報工学コース 知的コンピューティング学研究室
特別研究（令和7年度） — 小田 晴大
指導教員: 林 冬惠 准教授

---

## 研究概要

大規模言語モデル（LLM）を用いたマルチエージェントシミュレーション（MAS）では、エージェントが完全に自律的に動作するため、役割からの逸脱・議題からの逸脱・ハルシネーションといった問題が生じ、シミュレーションの品質が低下する。

本研究では、Microsoft 製のシミュレーション環境 [TinyTroupe](https://github.com/microsoft/TinyTroupe) を基盤とし、Human-in-the-Loop の概念を導入することで、**人間がエージェントの行動生成過程に介入できる参加型シミュレーション環境**を設計・実装した。自律型と参加型の比較評価により、人間の介入がエージェント行動の品質、議論の協調過程、および最終成果物の質を向上させることを示した。

詳細は特別研究報告書「参加型LLMマルチエージェントシミュレーション環境の設計と実装」（令和8年2月）を参照。

## 設計方針

参加型機構の導入にあたり、以下の3つの方針を採用した。

- **最小限な介入と持続的な効果** — 介入は行動生成過程にのみ与え、その効果は後続の全ての行動生成に持続的に反映される。
- **選択的介入** — 全ての行動ではなく、逸脱や品質低下が見られた行動にのみ人間が介入する。
- **エージェントの自律性の尊重** — 事後介入（生成された行動を確認してから介入判断）を採用し、自律的な行動生成能力を活かす。

## 介入機構

エージェントが行動を生成するたびに、人間は以下の2択を選択する。

| 操作 | 説明 |
|------|------|
| **ACCEPT** | 生成された行動をそのまま承認 |
| **GUIDE** | ガイドラインを入力し、THINK（内省）の強制を経て行動を再生成 |

GUIDE で与えたフィードバックは **ガイドラインメモリ（Guideline Memory）** としてプロンプトに `system` メッセージとして注入され、シミュレーション終了まで累積的に保持される。これにより、単発の修正に留まらない持続的な行動改善を実現する。

ガイドラインは（1）役割・議題からの逸脱防止、（2）人間の視点・判断の反映、（3）ハルシネーションの抑制、の3つの目的で用いられる。

## 評価結果

評価シナリオ: **「スマート研究室案内デモの企画会議」**（オープンキャンパス向け）

- 3エージェント（Project Manager / Systems Engineer / AI Researcher）による設計会議
- LLM: `gpt-4o-mini`、5ステップ × 5試行
- 自律型条件 vs 参加型条件（PM のみに人間が介入）の比較

### ミクロ評価（個々のエージェント行動の品質、8項目ルーブリック）

5試行平均で参加型条件のスコアが全エージェントで上昇した。

| エージェント | 自律型 | 参加型 |
|-------------|-------:|-------:|
| Project Manager（介入対象） | 約 5.0 | 約 7.2 |
| Systems Engineer | 約 3.8 | 約 6.2 |
| AI Researcher | 約 4.4 | 約 5.2 |

特に **新規・具体的な提案 (A04)**、**議論の構造化・要約 (A07)**、**次ステップの提示 (A08)** で顕著な改善が見られた。介入対象でない Systems Engineer / AI Researcher も、PM の議論進行改善によりタスク分解が促され、間接的に行動品質が向上した。

### マクロ評価（シミュレーション全体）

| 評価対象 | 自律型 | 参加型 |
|---------|-------:|-------:|
| 協調過程ルーブリック（6項目） | 平均 3.4/6 | 平均 5.8/6 |
| 成果物の達成（5項目） | 平均 3.0/5 | 平均 4.8/5 |

特に **次ステップの明示 (S01)**、**議論要約・チェックポイント (S05)**、**明示的な合意 (S06)** で大きな差が生じた。成果物の具体性（技術要素・体験フロー等）も参加型条件で大幅に向上した。

これらの結果から、人間の行動生成過程への介入がエージェント行動の品質向上に留まらず、シミュレーション全体の協調過程と成果物の質の向上にも寄与することを示した。

## 主な実装範囲

★ 印は本研究で新規追加したファイル、無印は TinyTroupe 由来のファイルを示す。

### 参加型機構（本研究の中核）

```
tinytroupe/agent/
├── ★ participatory_tiny_person.py    # 参加型エージェント（TinyPerson を継承）
├── ★ participatory_utils.py          # HumanIntervention、変換ユーティリティ
└── tiny_person.py                    # ベースクラス（TinyTroupe）
```

`ParticipatoryTinyPerson` は `TinyPerson` を継承し、`HumanIntervention` クラスとの連携で人間介入機構を実現する。`TinyWorld`（環境）は `TinyPerson` のみに依存するため、自律型エージェントと参加型エージェントを同一の環境内で混在させて動作させることができる。

### 評価パイプライン（本研究の評価フレームワーク）

`tinytroupe/evaluation/` ディレクトリは全て新規実装。Evidence-Centered Design の考え方に基づき、協調過程の質を観測可能なルーブリックに落とし込んでいる。

```
tinytroupe/evaluation/                     # ★ ディレクトリ全体が新規
├── ★ micro_evaluation.py                  # ミクロ評価（LLM-as-a-judge / 8項目）
├── ★ macro_evaluation.py                  # マクロ評価（協調過程・成果物 / 6項目）
├── ★ process_metrics.py                   # プロセス指標（停滞率・発散カウント）
├── ★ deliverables.py                      # 評価対象の成果物定義
└── ★ complete_evaluation_pipeline.py      # 統合実行
```

### 評価シナリオ・ペルソナ・実行スクリプト

```
├── ★ Tutorial_participatory.py            # 参加型シミュレーション実行
├── ★ run_autonomous_only.py               # 自律型条件の実行
├── ★ micro_rubric_evaluation.py           # ミクロ評価実行
├── ★ macro_rubric_evaluation.py           # マクロ評価実行
├── ★ deliverables_rubric_evaluation.py    # 成果物評価実行
├── ★ agent_specs/                         # 評価シナリオのペルソナ定義（PM / SE / AI Researcher）
├── ★ evaluation_results/                  # 評価結果 JSON
├── ★ simulation_results/                  # シミュレーションログ
└── ★ rubric_results/                      # ルーブリック評価結果
```

### 探索的実装（報告書本論には含めなかった追加実装）

設計検討・拡張可能性の検証として実装した試行的なコンポーネント。報告書では介入オプションとして MODIFY を不採用としているが、MODIFY 系の検証コードも残っている。

- ★ `tinytroupe/agent/human_action_generator.py`, `human_controlled_person.py`, `human_corrector.py` — 人間が直接エージェントを操作する形式（MODIFY 系介入の検証用）
- ★ `tinytroupe/agent/learnable_tiny_person.py`, `learnable_utils.py` — 学習可能エージェントの試作
- ★ `refine_persona.py` — 参加型介入で得られたガイドラインを LLM で分析し、エージェントのペルソナ定義（JSON）に反映する試作
- ★ `evaluate_refined.py` — 洗練後ペルソナの評価
- ★ `try/` — 初期検討用のブレインストーミング素材

### ベースフレームワーク（Microsoft TinyTroupe 由来）

`tinytroupe/agent/tiny_person.py`、`tinytroupe/environment/`、`tinytroupe/extraction/`、`tinytroupe/factory/`、`tinytroupe/openai_utils.py`、`tinytroupe/steering/`、`tinytroupe/tools/`、`tinytroupe/validation/`、`examples/` などはオリジナルの [TinyTroupe](https://github.com/microsoft/TinyTroupe) に由来する。

## 技術スタック

- **言語**: Python
- **モデル**: OpenAI API — `gpt-4o-mini`（シミュレーション・評価）、`o3-mini`（詳細推論）、`text-embedding-3-small`
- **評価手法**: LLM-as-a-judge、ルーブリックベース評価、Evidence-Centered Design に基づく指標設計
- **基盤フレームワーク**: Microsoft [TinyTroupe](https://github.com/microsoft/TinyTroupe)（MIT License）

## セットアップと実行

```bash
# 環境変数
export OPENAI_API_KEY="your-api-key"

# 参加型シミュレーション
python Tutorial_participatory.py

# 自律型シミュレーション
python run_autonomous_only.py

# 評価
python micro_rubric_evaluation.py
python macro_rubric_evaluation.py
```

モデル・トークン上限・キャッシュ等の設定は `config.ini` で管理する。

## ライセンス

本リポジトリは Microsoft Corporation 製の [TinyTroupe](https://github.com/microsoft/TinyTroupe)（MIT License）を基盤とし、参加型機構・評価パイプラインを拡張したものである（`LICENSE` 参照）。
本研究で新規追加した部分（★ 印のあるファイル）も同じく MIT License の下で公開する。

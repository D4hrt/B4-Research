# TinyTroupe Participatory

**参加型LLMマルチエージェントシミュレーションの設計と実装**

B4（2025年度）研究プロジェクト

## 概要

LLMマルチエージェントシミュレーションにおいて、以下の課題に対処するため**参加型（Participatory）アプローチ**を提案・実装したものです。

- 長期的な行動の一貫性の欠如
- 役割からの逸脱
- 議論の停滞

MicrosoftのLLMマルチエージェントシミュレーションフレームワーク [TinyTroupe](https://github.com/microsoft/TinyTroupe) を基盤とし、人間がシミュレーションに介入してエージェントの行動を誘導する仕組みを新たに設計・実装しました。

## 参加型アプローチ

エージェントが行動を生成するたびに、人間は以下の2つの選択肢から介入方法を選びます。

| 操作 | 説明 |
|------|------|
| **ACCEPT** | エージェントの行動をそのまま承認 |
| **GUIDE** | ガイドラインを入力し、行動を再生成させる |

GUIDEで蓄積されたガイドラインは、認知科学の**作業記憶（Working Memory）** の目標維持機能をモデル化しており、一度与えた指示が後続の**全ての行動生成に持続的に影響**します。

## TinyTroupeからの拡張点

### 1. 参加型エージェント（`ParticipatoryTinyPerson`）

- `TinyPerson` を継承し、ACCEPT / GUIDE の2択で人間が介入可能なエージェントを実装
- GUIDE時にはTHINK（内省）アクションを強制生成し、ガイドラインを内面化してから行動を再生成
- ガイドラインはシステムメッセージとしてプロンプトに注入され、TinyTroupeのEpisodic / Semantic Memoryと整合
- 既存の `TinyPerson` インスタンスを `convert_to_participatory()` で変換可能

### 2. 人間操作エージェント（`HumanControlledPerson`）

- `ActionGenerator` を `HumanActionGenerator` に差し替え、人間が直接 TALK / THINK / DONE コマンドで操作するエージェントを実装

### 3. 3層評価パイプライン（`tinytroupe/evaluation/`）

TinyTroupeには存在しなかった体系的な評価モジュールを新規開発しました。

| 評価層 | クラス | 手法 | 内容 |
|--------|--------|------|------|
| **ミクロ評価** | `MicroEvaluator` | LLM-as-a-judge | エージェント個別の行動品質（役割一貫性・論理的一貫性・議題遵守、各5点満点） |
| **マクロ評価** | `MacroEvaluator` | TinyTroupeの`ResultsExtractor` + LLM-as-a-judge | シミュレーション全体の成果物品質・合意形成成功率・技術矛盾の検出 |
| **プロセス指標** | `ProcessMetrics` | LLM不使用の定量計算 | 停滞率（Jaccard類似度ベース）・発散回数（議題との類似度） |

`MeetingEvaluator` がこれらを統合実行し、JSON形式で結果を保存します。

### 4. ペルソナ自動洗練（`refine_persona.py`）

シミュレーション履歴をGPT-4oで分析し、エージェントのペルソナ定義（JSON）を自動的に洗練する機能を実装。参加型介入の知見をペルソナ改善に反映し、自律シミュレーションでも活用可能にしました。

## プロジェクト構成

```
├── Tutorial_participatory.py     # 参加型シミュレーションのメインスクリプト
├── run_autonomous_only.py        # 自律条件シミュレーション実行
├── refine_persona.py             # ペルソナ自動洗練
├── *_rubric_evaluation.py        # 各種ルーブリック評価スクリプト
├── evaluate_refined.py           # 洗練後ペルソナの評価
├── config.ini                    # モデル・パラメータ設定
├── agent_specs/                  # エージェントのペルソナ定義（JSON）
├── evaluation_results/           # 評価結果（JSON）
├── simulation_results/           # シミュレーション結果
├── tinytroupe/                   # TinyTroupeフレームワーク（拡張版）
│   ├── agent/
│   │   ├── participatory_tiny_person.py   # 参加型エージェント
│   │   ├── participatory_utils.py         # 変換ユーティリティ
│   │   ├── human_action_generator.py      # 人間操作用ActionGenerator
│   │   ├── human_controlled_person.py     # 人間操作エージェント
│   │   └── ...
│   ├── evaluation/
│   │   ├── micro_evaluation.py            # ミクロ評価
│   │   ├── macro_evaluation.py            # マクロ評価
│   │   ├── process_metrics.py             # プロセス指標
│   │   ├── complete_evaluation_pipeline.py # 統合パイプライン
│   │   └── deliverables.py               # 成果物定義
│   └── ...
└── examples/                     # Jupyter Notebookサンプル
```

## セットアップ

### 1. 環境変数の設定

```bash
export OPENAI_API_KEY="your-api-key"
```

### 2. 実行例

```bash
# 参加型シミュレーション
python Tutorial_participatory.py

# 自律条件シミュレーション
python run_autonomous_only.py

# ペルソナ洗練
python refine_persona.py
```

## 評価シナリオ

オープンキャンパス向け「**Smart Lab Demo**」設計会議のシミュレーションを用いて評価しました。3名のエージェント（PM・Systems Engineer・AI Researcher）が、IoT・LLM・MCPを統合したデモの設計を議論します。

自律条件と参加型条件でシミュレーションを複数回実行し、3層評価パイプラインにより比較分析を行いました。

## ベースフレームワーク

- [Microsoft TinyTroupe](https://github.com/microsoft/TinyTroupe) — LLM-powered multiagent persona simulation

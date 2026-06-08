"""
TinyTroupe Evaluation Module

評価モジュール - シミュレーション品質の定量評価

構成:
- MicroEvaluator: エージェント行動品質評価 (LLM-as-a-judge)
  - persona_consistency: 役割一貫性
  - logical_consistency: 論理的一貫性
  - task_adherence: 議題遵守

- MacroEvaluator: シミュレーション成果評価 (ハイブリッド)
  - 成果物抽出: ResultsExtractor
  - 品質評価: LLM-as-a-judge
  - 矛盾検出: LLM-as-a-judge

- ProcessMetrics: プロセス指標 (LLM不使用)
  - turns_to_consensus: ターン数
  - stagnation_rate: 停滞率
  - divergence_count: 発散回数

- MeetingEvaluator: 統合パイプライン
"""

# Deliverables definition
from .deliverables import REQUIRED_DELIVERABLES

# Micro evaluation (LLM-as-a-judge)
from .micro_evaluation import MicroEvaluator

# Macro evaluation (Hybrid: ResultsExtractor + LLM)
from .macro_evaluation import MacroEvaluator

# Process metrics (No LLM)
from .process_metrics import ProcessMetrics

# Complete pipeline
from .complete_evaluation_pipeline import MeetingEvaluator, CompleteMeetingEvaluator

__all__ = [
    'REQUIRED_DELIVERABLES',
    'MicroEvaluator',
    'MacroEvaluator',
    'ProcessMetrics',
    'MeetingEvaluator',
    'CompleteMeetingEvaluator'  # 後方互換性
]
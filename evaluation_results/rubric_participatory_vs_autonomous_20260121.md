**Rubric: Participatory vs Autonomous (binary-quality JSON rubric)**

Evaluate your simulation results against this quality rubric. Each item is scored as 1 (true) or 0 (false). The evaluator should return a JSON object mapping item keys to 1 or 0.

Example output schema:

```json
{
  "persona_consistency": 1,
  "logical_consistency": 1,
  "task_adherence": 0,
  "deliverables_complete": 1,
  "deliverables_concrete": 0,
  "deliverables_feasible": 1,
  "role_assignment_clear": 0,
  "resources_specific": 0,
  "consensus_achieved": 0,
  "turns_efficiency": 0,
  "low_stagnation": 0,
  "low_divergence": 0,
  "intervention_balance": 1,
  "guideline_persistence": 1,
  "overall_deliverable_quality": 0
}
```

Rubric items (15):

- `persona_consistency`: Agent behavior stays aligned with assigned persona/role. Evidence: `micro_evaluation.overall_average.persona_consistency` in the evaluation reports.

- `logical_consistency`: No major logical contradictions or broken reasoning in agent outputs. Evidence: `micro_evaluation.overall_average.logical_consistency`.

- `task_adherence`: Agents remain on-topic and relevant to meeting requirements. Evidence: `micro_evaluation.overall_average.task_adherence` and `process_metrics.divergence`.

- `deliverables_complete`: All required deliverables are present (central_concept, experience_flow, technical_architecture, role_assignment, required_resources). Evidence: `macro_evaluation.consensus.completeness_rate` and `macro_evaluation.deliverables`.

- `deliverables_concrete`: Deliverables include concrete details (durations, device models, steps). Evidence: `macro_evaluation.deliverables_quality.*.concreteness`.

- `deliverables_feasible`: Deliverables are realistic given stated resources. Evidence: `macro_evaluation.deliverables_quality.*.feasibility`.

- `role_assignment_clear`: Roles include assignee and deadlines. Evidence: `macro_evaluation.deliverables.role_assignment`.

- `resources_specific`: Required resources list includes quantities, types, or budget estimates. Evidence: `macro_evaluation.deliverables.required_resources` and `deliverables_quality.required_resources`.

- `consensus_achieved`: MacroEvaluator reports consensus success (`macro_evaluation.consensus.success == true`).

- `turns_efficiency`: Turns-to-consensus is low enough to be considered efficient (example threshold: < 20 turns). Evidence: `process_metrics.turns_to_consensus` and `process_metrics.efficiency_rating`.

- `low_stagnation`: Stagnation rate is low (example threshold: < 0.85). Evidence: `process_metrics.stagnation.stagnation_rate`.

- `low_divergence`: Divergence rate/topic similarity indicates discussion stayed on topic (example threshold for divergence_rate < 0.3). Evidence: `process_metrics.divergence.divergence_rate` or `divergence_count`.

- `intervention_balance`: (participatory only) Intervention mix is reasonable (not dominated by repeated GUIDEs or none). Evidence: `intervention_stats.by_type` and `intervention_stats.total`.

- `guideline_persistence`: Added guidelines are reflected in subsequent agent actions (observable via changes in `macro_evaluation.deliverables` or interaction transcripts).

- `overall_deliverable_quality`: Macro-level overall quality meets a minimal threshold (example: `macro_evaluation.deliverables_quality.overall_quality >= 3`).

Evidence files:
- `evaluation_results/participatory_20260121_035714.json`
- `evaluation_results/autonomous_20260121_034041.json`

Usage:
- For each item, set 1 if the condition is met, otherwise 0.
- Return the JSON object with all keys present.
  - Scoring: 1（反映なし/矛盾を産む）〜5（明確に行動に影響し、改善を示す）
  - Evidence: `intervention_stats.guidelines` と `macro_evaluation.deliverables` の変化（参加型レポート）

- **Overall Deliverable Quality**: マクロ評価での総合品質スコア。
  - Scoring: 1（低）〜5（高）
  - Evidence: `macro_evaluation.deliverables_quality.overall_quality`

補足:
- 参照ファイル:
  - [evaluation_results/participatory_20260121_035714.json](evaluation_results/participatory_20260121_035714.json)
  - [evaluation_results/autonomous_20260121_034041.json](evaluation_results/autonomous_20260121_034041.json)

使用法:
- 各項目を1–5点で採点し，必要に応じて短い根拠コメント（1行）を付与してください。
- 最終スコアは単純平均または重み付け平均（要定義）で算出できます。

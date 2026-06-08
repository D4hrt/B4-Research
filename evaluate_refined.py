"""
evaluate_refined.py - 洗練ペルソナシミュレーション結果のバッチ評価

マクロ評価（M01-M06）とミクロ評価（A01-A08）を
洗練ペルソナのシミュレーション結果に対して一括実行する。
"""

import openai
import os
import json
import re
from datetime import datetime
from pathlib import Path

# OpenAI APIキー（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

MODEL = "gpt-4o"

# ============================================================================
# 評価対象の定義
# ============================================================================
TARGETS = {
    "refined_participatory": {
        "world": "simulation_results/refined_participatory_20260227_143451.txt",
        "agents": {
            "Emily_Carter": "simulation_results/agents_results/refined_participatory_Emily_Carter_20260227_143451.txt",
            "Daniel_Thompson": "simulation_results/agents_results/refined_participatory_Daniel_Thompson_20260227_143451.txt",
            "Sophia_Mitchell": "simulation_results/agents_results/refined_participatory_Sophia_Mitchell_20260227_143451.txt",
        },
    },
    "refined_autonomous": {
        "world": "simulation_results/refined_autonomous_20260227_144209.txt",
        "agents": {
            "Emily_Carter": "simulation_results/agents_results/refined_autonomous_Emily_Carter_20260227_144209.txt",
            "Daniel_Thompson": "simulation_results/agents_results/refined_autonomous_Daniel_Thompson_20260227_144209.txt",
            "Sophia_Mitchell": "simulation_results/agents_results/refined_autonomous_Sophia_Mitchell_20260227_144209.txt",
        },
    },
}

# ============================================================================
# ペルソナ情報のロード
# ============================================================================
PERSONA_MAP = {
    "Emily_Carter": "./agent_specs/pm_participatory.json",
    "Daniel_Thompson": "./agent_specs/engineer_participatory.json",
    "Sophia_Mitchell": "./agent_specs/ai_researcher_participatory.json",
}

def load_persona_info(agent_key: str) -> dict:
    spec_path = PERSONA_MAP.get(agent_key, "")
    if not os.path.exists(spec_path):
        return {"name": "", "occupation_title": "", "occupation_description": ""}
    with open(spec_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    persona = data.get("persona", {})
    occ = persona.get("occupation", {})
    return {
        "name": persona.get("name", ""),
        "occupation_title": occ.get("title", ""),
        "occupation_description": occ.get("description", ""),
    }

# ============================================================================
# Rubric定義
# ============================================================================
MACRO_RUBRIC = """
M01_next_actions_are_explicit:
- The plan includes explicit next actions (e.g., ToDo items, testing plan, preparation steps, deadlines).
M02_concrete_examples_in_deliverables:
- The plan includes concrete examples (e.g., specific demo actions, devices, scenarios, or what visitors will do).
M03_concrete_technical_elements_named:
- The plan names at least one concrete technical element (e.g., specific sensors, protocols, system components, MCP server/tooling, LLM model, data pipeline).
M04_discussion_progresses_across_agenda:
- The conversation meaningfully progresses across multiple deliverable dimensions (not stuck repeatedly on one topic).
M05_midway_summary_or_checkpoint_present:
- At least one explicit summary/checkpoint appears (e.g., "So far we decided…", "Let's summarize…").
M06_explicit_agreement_or_decision_present:
- The conversation includes an explicit agreement/decision statement that clearly specifies what is being agreed/decided (e.g., "we decide to use X for the demo", "we finalize the flow as …").
"""

MICRO_RUBRIC = """
A01_role_aligned_contribution_present:
- The agent makes at least one contribution that clearly matches its expected team role and is expressed with actionable specificity.
- To score 1, the contribution must satisfy both conditions below:
  1. Role alignment: The content is explicitly aligned with the agent's role responsibilities (e.g., PM: facilitation, agenda/structure, decision convergence, task assignment; Engineer: technical design, integration details, feasibility constraints; Researcher: rationale, evaluation/metrics, literature framing).
  2. Concrete substance: The contribution includes at least one concrete element such as a specific deliverable, a step-by-step plan, named components/devices/tools, an explicit decision proposal, or a clearly stated task/action item (not just generic encouragement or restating others).
- If the agent only provides generic encouragement ("sounds good"), vague guidance ("we should plan"), or role-like statements without concrete substance, score 0.
A02_on_topic_most_of_time:
- The agent stays on the task for the majority of its turns, and does not exhibit sustained derailment.
A03_no_self_contradiction:
- The agent does not contradict (i) its own earlier statements without explicit correction, or (ii) the stated requirements/constraints.
A04_novel_concrete_proposal_present:
- The agent proposes at least one novel and concrete idea (not merely repeating others).
A05_references_or_builds_on_others:
- The agent explicitly references or builds on another participant's point (agreement + extension, or incorporation).
A06_improves_or_critiques_ideas:
- The agent provides improvement, critique, tradeoff analysis, or refinement of an idea (not only praise).
A07_structures_or_summarizes_discussion:
- The agent provides a structured recap/summary (e.g., bullet points, numbered list, or clearly separated sections) that includes at least two of the following three components:
  1. Decisions made (what has been agreed/finalized),
  2. Open issues (what is still undecided or needs clarification),
  3. Next actions (what should be done next).
- If the agent only restates ideas without structure, or provides a recap that contains fewer than two of the components above, score 0.
A08_drives_decision_or_next_steps:
- The agent pushes the discussion toward actionable outcomes by proposing next steps that include at least two of the following four elements:
  1. Assignee (who will do it),
  2. Action (what will be done),
  3. Time constraint (when / by what deadline / within what time),
  4. Validation (how to confirm it works, e.g., a test, demo rehearsal, checklist).
- Generic statements such as "we should do X" or "let's consider X" without at least two elements above should be scored 0.
"""

# ============================================================================
# LLM呼び出し共通
# ============================================================================
def call_llm(system_msg: str, user_msg: str) -> dict:
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        return json.loads(text)
    except json.JSONDecodeError:
        matches = re.findall(r"\{.*\}", text, re.DOTALL)
        for m in reversed(matches):
            try:
                return json.loads(m)
            except Exception:
                continue
        return {"__parse_error__": text[:200]}
    except Exception as e:
        return {"__api_error__": str(e)}


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ============================================================================
# マクロ評価
# ============================================================================
def run_macro_evaluation(world_path: str) -> dict:
    log = load_text(world_path)
    prompt = f"""
Evaluate the following simulation history against the rubric below.

Instructions:
- For each rubric item, output 1 if the item is satisfied, otherwise output 0.
- Use ONLY the provided simulation history as evidence. Do not assume missing details.
- If the item is not explicitly supported by the history, output 0.
- Return VALID JSON ONLY (no explanations, no markdown, no extra keys).

Output JSON format:
{{
    "macro": {{
        "M01_next_actions_are_explicit": 0,
        "M02_concrete_examples_in_deliverables": 0,
        "M03_concrete_technical_elements_named": 0,
        "M04_discussion_progresses_across_agenda": 0,
        "M05_midway_summary_or_checkpoint_present": 0,
        "M06_explicit_agreement_or_decision_present": 0
    }}
}}

Macro Rubric (judge each item as True=1 / False=0):
{MACRO_RUBRIC}

Simulation History:
{log}
"""
    return call_llm(
        "You are an expert evaluator of multi-agent simulation outcomes.",
        prompt,
    )


# ============================================================================
# ミクロ評価
# ============================================================================
def run_micro_evaluation(agent_path: str, agent_key: str) -> dict:
    log = load_text(agent_path)
    persona = load_persona_info(agent_key)

    prompt = f"""
Evaluate the SINGLE AGENT trajectory below against the rubric using the provided Persona Definition.

Instructions:
- For each rubric item, output 1 if the item is satisfied, otherwise output 0.
- Use ONLY the provided agent trajectory as evidence. Do not assume missing details.
- If the item is not explicitly supported by the trajectory, output 0.
- Return VALID JSON ONLY (no explanations, no markdown, no extra keys).

Persona Definition (use ONLY for judging role alignment; do not infer missing actions):
- Agent Name: {persona['name']}
- Occupation title: {persona['occupation_title']}
- Occupation description: {persona['occupation_description']}

Output JSON format:
{{
    "micro": {{
        "A01_role_aligned_contribution_present": 0,
        "A02_on_topic_most_of_time": 0,
        "A03_no_self_contradiction": 0,
        "A04_novel_concrete_proposal_present": 0,
        "A05_references_or_builds_on_others": 0,
        "A06_improves_or_critiques_ideas": 0,
        "A07_structures_or_summarizes_discussion": 0,
        "A08_drives_decision_or_next_steps": 0
    }}
}}

Micro Rubric (judge each item as True=1 / False=0):
{MICRO_RUBRIC}

Agent Trajectory:
{log}
"""
    return call_llm(
        "You are an expert evaluator of agent behavior quality in multi-agent simulations.",
        prompt,
    )


# ============================================================================
# メイン
# ============================================================================
def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join("rubric_results", f"refined_eval_{timestamp}")
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    all_results = {}

    for condition, paths in TARGETS.items():
        print(f"\n{'=' * 70}")
        print(f"📊 {condition} の評価")
        print(f"{'=' * 70}")

        condition_results = {"macro": None, "micro": {}}

        # --- マクロ評価 ---
        print(f"\n  🔍 マクロ評価: {paths['world']}")
        macro = run_macro_evaluation(paths["world"])
        condition_results["macro"] = macro
        macro_scores = macro.get("macro", {})
        macro_sum = sum(macro_scores.values()) if macro_scores else "N/A"
        print(f"     結果: {macro_scores}")
        print(f"     合計: {macro_sum}/6")

        # --- ミクロ評価（エージェント別）---
        for agent_key, agent_path in paths["agents"].items():
            print(f"\n  🔍 ミクロ評価: {agent_key}")
            micro = run_micro_evaluation(agent_path, agent_key)
            condition_results["micro"][agent_key] = micro
            micro_scores = micro.get("micro", {})
            micro_sum = sum(micro_scores.values()) if micro_scores else "N/A"
            print(f"     結果: {micro_scores}")
            print(f"     合計: {micro_sum}/8")

        all_results[condition] = condition_results

    # ========================================================================
    # 結果の保存
    # ========================================================================
    result_path = os.path.join(output_dir, "evaluation_results.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 評価結果を保存: {result_path}")

    # ========================================================================
    # 比較サマリー
    # ========================================================================
    print(f"\n{'=' * 70}")
    print(f"📈 比較サマリー")
    print(f"{'=' * 70}")

    print(f"\n{'条件':<30} {'マクロ合計':>10} {'ミクロ平均':>10}")
    print(f"{'─' * 52}")

    for condition, res in all_results.items():
        macro_scores = res.get("macro", {}).get("macro", {})
        macro_total = sum(macro_scores.values()) if macro_scores else 0

        # ミクロ: 全エージェントの平均
        micro_totals = []
        for agent_key, micro_res in res.get("micro", {}).items():
            scores = micro_res.get("micro", {})
            if scores:
                micro_totals.append(sum(scores.values()))
        micro_avg = sum(micro_totals) / len(micro_totals) if micro_totals else 0

        print(f"{condition:<30} {macro_total:>8}/6 {micro_avg:>8.1f}/8")

    # マクロ項目別の比較
    print(f"\n--- マクロ評価 項目別比較 ---")
    macro_items = [
        "M01_next_actions_are_explicit",
        "M02_concrete_examples_in_deliverables",
        "M03_concrete_technical_elements_named",
        "M04_discussion_progresses_across_agenda",
        "M05_midway_summary_or_checkpoint_present",
        "M06_explicit_agreement_or_decision_present",
    ]
    header = f"{'項目':<45}"
    for cond in all_results:
        header += f" {cond:>25}"
    print(header)
    print("─" * (45 + 26 * len(all_results)))
    for item in macro_items:
        row = f"{item:<45}"
        for cond, res in all_results.items():
            val = res.get("macro", {}).get("macro", {}).get(item, "?")
            row += f" {val:>25}"
        print(row)

    # ミクロ項目別の比較（エージェント平均）
    print(f"\n--- ミクロ評価 項目別比較（エージェント平均）---")
    micro_items = [
        "A01_role_aligned_contribution_present",
        "A02_on_topic_most_of_time",
        "A03_no_self_contradiction",
        "A04_novel_concrete_proposal_present",
        "A05_references_or_builds_on_others",
        "A06_improves_or_critiques_ideas",
        "A07_structures_or_summarizes_discussion",
        "A08_drives_decision_or_next_steps",
    ]
    header = f"{'項目':<45}"
    for cond in all_results:
        header += f" {cond:>25}"
    print(header)
    print("─" * (45 + 26 * len(all_results)))
    for item in micro_items:
        row = f"{item:<45}"
        for cond, res in all_results.items():
            vals = []
            for agent_key, micro_res in res.get("micro", {}).items():
                v = micro_res.get("micro", {}).get(item, 0)
                vals.append(v)
            avg = sum(vals) / len(vals) if vals else 0
            row += f" {avg:>23.2f}/1"
        print(row)

    print(f"\n✅ 評価完了: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

import openai
import os
import json
import re
from datetime import datetime
from pathlib import Path

# OpenAI APIキー（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"


# Rubric評価基準
rubric_criteria = """
A01_role_aligned_contribution_present:
- The agent makes at least one contribution that clearly matches its expected team role and is expressed with actionable specificity.
- To score 1, the contribution must satisfy both conditions below:
  1. Role alignment: The content is explicitly aligned with the agent’s role responsibilities (e.g., PM: facilitation, agenda/structure, decision convergence, task assignment; Engineer: technical design, integration details, feasibility constraints; Researcher: rationale, evaluation/metrics, literature framing).
  2. Concrete substance: The contribution includes at least one concrete element such as a specific deliverable, a step-by-step plan, named components/devices/tools, an explicit decision proposal, or a clearly stated task/action item (not just generic encouragement or restating others).
- If the agent only provides generic encouragement (“sounds good”), vague guidance (“we should plan”), or role-like statements without concrete substance, score 0.
A02_on_topic_most_of_time:
- The agent stays on the task for the majority of its turns, and does not exhibit sustained derailment.
A03_no_self_contradiction:
- The agent does not contradict (i) its own earlier statements without explicit correction, or (ii) the stated requirements/constraints.
A04_novel_concrete_proposal_present:
- The agent proposes at least one novel and concrete idea (not merely repeating others).
A05_references_or_builds_on_others:
- The agent explicitly references or builds on another participant’s point (agreement + extension, or incorporation).
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
- Generic statements such as “we should do X” or “let’s consider X” without at least two elements above should be scored 0.
"""

# シミュレーション履歴をテキストファイルから読み込む関数
def load_agent_log(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        log = file.read()
    return log

# プロンプトを作成し、LLMに評価を依頼する関数
def create_prompt(file_path, agent_name):
    agent_log = load_agent_log(file_path)
    
    # ペルソナ情報を読み込む
    persona = load_persona(agent_name)
    persona_name = persona.get("name", "")
    occupation_title = persona.get("occupation_title", "")
    occupation_description = persona.get("occupation_description", "")

    # プロンプトを作成
    prompt = f"""
Evaluate the SINGLE AGENT trajectory below against the rubric using the provided Persona Definition.

Instructions:
- For each rubric item, output 1 if the item is satisfied, otherwise output 0.
- Use ONLY the provided agent trajectory as evidence. Do not assume missing details.
- If the item is not explicitly supported by the trajectory, output 0.
- Return VALID JSON ONLY (no explanations, no markdown, no extra keys).

Persona Definition (use ONLY for judging role alignment; do not infer missing actions):
- Agent Name: {persona_name}
- Occupation title: {occupation_title}
- Occupation description: {occupation_description}

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
{rubric_criteria}

Agent Trajectory:
{agent_log}
"""
    return prompt


def load_persona(agent_name: str) -> dict:
    # デフォルト
    result = {
        "name": "",
        "occupation_title": "",
        "occupation_description": ""
    }

    try:
        # Normalize agent_name to allow inputs like 'Emily_Carter' or 'Emily Carter'
        normalized = agent_name.replace('_', ' ').strip().lower()
        if normalized == 'emily carter' or agent_name == 'Emily_Carter':
            spec_file = 'pm_participatory.json'
        elif normalized == 'sophia mitchell' or agent_name == 'Sophia_Mitchell':
            spec_file = 'ai_researcher_participatory.json'
        elif normalized == 'daniel thompson' or agent_name == 'Daniel Thompson' or agent_name == 'Daniel_Thompson':
            spec_file = 'engineer_participatory.json'
        else:
            return result

        spec_path = os.path.join('.', 'agent_specs', spec_file)
        if not os.path.exists(spec_path):
            return result

        with open(spec_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        persona = data.get('persona', {})
        result['name'] = persona.get('name', '')
        occupation = persona.get('occupation', {})
        result['occupation_title'] = occupation.get('title', '')
        result['occupation_description'] = occupation.get('description', '')
        return result
    except Exception:
        return result

def evaluate_simulation(prompt):
    # LLMに評価を依頼する
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # 使用するモデル
            messages=[
                {"role": "system", "content": "You are an expert evaluator of agent behavior quality in multi-agent simulations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        return response.choices[0].message.content
    except Exception as e:
        # OpenAI client API may differ across installed versions; return a machine-parsable
        # error so the script doesn't crash during local runs without a compatible SDK.
        return json.dumps({"__api_error__": str(e)})


def parse_evaluation_response(text: str) -> dict:
    """
    Try to parse model output as JSON. If direct parse fails, attempt
    to extract a JSON substring. On failure, return a dict with error info.
    """
    try:
        return json.loads(text)
    except Exception:
        # Try to extract JSON-like substrings and parse the last one that parses
        matches = re.findall(r"\{.*\}", text, re.DOTALL)
        for m in reversed(matches):
            try:
                return json.loads(m)
            except Exception:
                continue
        # Give up: return parse error with raw text
        return {"__parse_error__": "Could not parse JSON from model output", "raw": text}

def save_evaluation_results(results, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

def main():
    # simulation_results/agents_results/participatory_Sophia_Mitchell_20260126_190642.txt
    file_name = "participatory_Sophia_Mitchell_20260126_190642"
    # Use relative paths so the script runs from the repo root
    file_path = os.path.join('.', 'simulation_results/agents_results', f"{file_name}.txt")

    # 評価の実行
    agent_name = "Sophia_Mitchell"
    prompt = create_prompt(file_path, agent_name)
    result_text = evaluate_simulation(prompt)

    # Parse model output into JSON/dict before saving
    parsed = parse_evaluation_response(result_text)

    condition = "micro"
    output_path = os.path.join('.', 'rubric_results/agents_results', f"{condition}_{file_name}.json")

    # Ensure output directory exists
    outdir = os.path.dirname(output_path)
    if outdir:
        Path(outdir).mkdir(parents=True, exist_ok=True)

    save_evaluation_results(parsed, output_path)
    print(f"Saved rubric evaluation to {output_path}")


if __name__ == "__main__":
    main()
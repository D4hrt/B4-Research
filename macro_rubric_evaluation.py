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
M01_next_actions_are_explicit:
- The plan includes explicit next actions (e.g., ToDo items, testing plan, preparation steps, deadlines).
M02_concrete_examples_in_deliverables:
- The plan includes concrete examples (e.g., specific demo actions, devices, scenarios, or what visitors will do).
M03_concrete_technical_elements_named:
- The plan names at least one concrete technical element (e.g., specific sensors, protocols, system components, MCP server/tooling, LLM model, data pipeline).
M04_discussion_progresses_across_agenda:
- The conversation meaningfully progresses across multiple deliverable dimensions (not stuck repeatedly on one topic).
M05_midway_summary_or_checkpoint_present:
- At least one explicit summary/checkpoint appears (e.g., “So far we decided…”, “Let’s summarize…”).
M06_explicit_agreement_or_decision_present:
- The conversation includes an explicit agreement/decision statement that clearly specifies what is being agreed/decided (e.g., “we decide to use X for the demo”, “we finalize the flow as …”).
"""

# シミュレーション履歴をテキストファイルから読み込む関数
def load_simulation_log(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        log = file.read()
    return log

# プロンプトを作成し、LLMに評価を依頼する関数
def create_prompt(file_path):
    simulation_log = load_simulation_log(file_path)
    
    # プロンプトを作成
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
{rubric_criteria}

Simulation History:
{simulation_log}
"""
    return prompt

def evaluate_simulation(prompt):
    # LLMに評価を依頼する
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",  # 使用するモデル
            messages=[
                {"role": "system", "content": "You are an expert evaluator of multi-agent simulation outcomes."},
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
    # simulation_results/participatory_20260126_190642.txt
    file_name = "participatory_20260126_190642"
    # Use relative paths so the script runs from the repo root
    file_path = os.path.join('.', 'simulation_results', f"{file_name}.txt")

    # 評価の実行
    prompt = create_prompt(file_path)
    result_text = evaluate_simulation(prompt)

    # Parse model output into JSON/dict before saving
    parsed = parse_evaluation_response(result_text)

    condition = "macro"
    output_path = os.path.join('.', 'rubric_results', f"{condition}_{file_name}.json")

    # Ensure output directory exists
    outdir = os.path.dirname(output_path)
    if outdir:
        Path(outdir).mkdir(parents=True, exist_ok=True)

    save_evaluation_results(parsed, output_path)
    print(f"Saved rubric evaluation to {output_path}")


if __name__ == "__main__":
    main()
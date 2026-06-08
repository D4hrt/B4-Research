import openai
import os
import json
import re
from datetime import datetime
from pathlib import Path

# OpenAI APIキー（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

rubric_criteria = """
(1) central_concept
- Required elements (ALL must be present to satisfy D11):
  a) Purpose/goal of the demo (what it demonstrates and why)
  b) Target audience fit (high school visitors; educational intent)
  c) Uniqueness/value proposition (what makes it special vs a generic demo)
D01: Is central_concept meaningfully discussed in the log?
D11: Are ALL required elements (a,b,c) explicitly and meaningfully covered in the log?
D21: Is central_concept specific (concrete purpose + concrete uniqueness; not vague)?

(2) experience_flow
- Required elements (ALL must be present to satisfy D12):
  a) Opening (how the demo starts / introduction)
  b) Main interaction (what visitors do hands-on)
  c) Closing (how it ends / takeaway)
  d) Duration constraint mention or plan (10–15 minutes)
D02: Is experience_flow meaningfully discussed in the log?
D12: Are ALL required elements (a,b,c,d) explicitly and meaningfully covered in the log?
D22: Is experience_flow specific (step-by-step or clearly sequenced; not generic)?


(3) technical_architecture
- Required elements (ALL must be present to satisfy D13):
  a) IoT components (devices/sensors/actuators or data sources)
  b) LLM/AI component (what the AI does)
  c) MCP/tool integration (how MCP/tools connect to the system)
  d) Integration method (data/control flow: how components interact)
D03: Is technical_architecture meaningfully discussed in the log?
D13: Are ALL required elements (a,b,c,d) explicitly and meaningfully covered in the log?
D23: Is technical_architecture specific (mentions concrete components AND concrete connections)?

(4) role_assignment
- Required elements (ALL must be present to satisfy D14):
  a) At least one explicit mapping of person/agent -> task/responsibility
  b) Coordination plan (how tasks fit together; handoffs or order)
D04: Is role_assignment meaningfully discussed in the log?
D14: Are ALL required elements (a,b) explicitly and meaningfully covered in the log?
D24: Is role_assignment specific (named assignees + named tasks; not vague “someone will do”)?

(5) required_resources
- Required elements (ALL must be present to satisfy D15):
  a) Devices/equipment list
  b) Personnel/roles needed
  c) Preparation time/schedule (setup/testing)
D05: Is required_resources meaningfully discussed in the log?
D15: Are ALL required elements (a,b,c) explicitly and meaningfully covered in the log?
D25: Is required_resources specific (named items and timeframes; not generic)?
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
Evaluate whether the discussion contains the following deliverable categories, whether required elements are satisfied, and whether the content is specific.

Instructions:
- Score each item as 1 (true) or 0 (false).
- Use ONLY the provided simulation history as evidence. Do not assume missing details.
- If the required information is not explicitly present in the log, output 0.
- "present" means the category is meaningfully discussed (not just a single vague mention).
- "required_elements_satisfied" means ALL required elements listed for that category are explicitly and meaningfully covered in the log.
- "specific" means the log includes concrete details (step-by-step flow, named devices/components, explicit role->task assignment, time/quantity constraints, integration flow). Generic/vague statements => 0.
- Return VALID JSON ONLY (no explanations, no markdown, no extra keys).

Output JSON format:
{{
    "deliverables_eval": {{
    "D01_central_concept_present_in_log": 0,
    "D02_experience_flow_present_in_log": 0,
    "D03_technical_architecture_present_in_log": 0,
    "D04_role_assignment_present_in_log": 0,
    "D05_required_resources_present_in_log": 0,

    "D11_central_concept_required_elements_satisfied": 0,
    "D12_experience_flow_required_elements_satisfied": 0,
    "D13_technical_architecture_required_elements_satisfied": 0,
    "D14_role_assignment_required_elements_satisfied": 0,
    "D15_required_resources_required_elements_satisfied": 0,

    "D21_central_concept_specific": 0,
    "D22_experience_flow_specific": 0,
    "D23_technical_architecture_specific": 0,
    "D24_role_assignment_specific": 0,
    "D25_required_resources_specific": 0
    }}
}}

Rubric questions and required elements:
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
                {"role": "system", "content": "You are an expert evaluator of multi-agent simulation deliverables."},
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

    condition = "deliverables"
    output_path = os.path.join('.', 'rubric_results/deliverables_results', f"{condition}_{file_name}.json")

    # Ensure output directory exists
    outdir = os.path.dirname(output_path)
    if outdir:
        Path(outdir).mkdir(parents=True, exist_ok=True)

    save_evaluation_results(parsed, output_path)
    print(f"Saved rubric evaluation to {output_path}")


if __name__ == "__main__":
    main()
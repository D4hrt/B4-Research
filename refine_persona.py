"""
refine_persona.py - シミュレーション履歴に基づくペルソナ洗練スクリプト

自律型または参加型シミュレーションの履歴を分析し、
各エージェントのペルソナJSONを洗練（リファイン）する。

使い方:
    # 参加型履歴から洗練
    python refine_persona.py --condition participatory

    # 自律型履歴から洗練
    python refine_persona.py --condition autonomous

    # 特定のトランスクリプトを指定
    python refine_persona.py --condition participatory --transcript simulation_results/participatory_20260126_190642.txt

    # 複数トランスクリプトを統合して洗練（デフォルト: 最新1件）
    python refine_persona.py --condition autonomous --use-all
"""

import openai
import os
import sys
import json
import re
import glob
import argparse
from datetime import datetime
from pathlib import Path
from copy import deepcopy

# ============================================================================
# 設定
# ============================================================================

# OpenAI APIキー（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

REFINEMENT_MODEL = "gpt-4o"  # 洗練に使用するモデル
TEMPERATURE = 0.3             # ある程度の創造性を許容

# エージェント定義ファイルのパス
AGENT_SPECS = {
    "Emily Carter": "./agent_specs/pm_participatory.json",
    "Daniel Thompson": "./agent_specs/engineer_participatory.json",
    "Sophia Mitchell": "./agent_specs/ai_researcher_participatory.json",
}

# シミュレーション結果ディレクトリ
SIMULATION_DIR = "./simulation_results"

# 洗練結果の出力先ベースディレクトリ
OUTPUT_BASE_DIR = "./agent_specs"


# ============================================================================
# ペルソナJSON構造の定義（プロンプトに含める参考情報）
# ============================================================================

PERSONA_STRUCTURE_DESCRIPTION = """
The persona JSON has the following top-level structure:
{
    "type": "TinyPerson",
    "current_episode_event_count": 0,
    "mental_faculties": [],
    "persona": {
        "name": "...",
        "age": ...,
        "nationality": "...",
        "country_of_residence": ...,
        "occupation": {
            "title": "...",
            "organization": "...",
            "description": "..."
        },
        "gender": "...",
        "residence": "...",
        "education": "...",
        "long_term_goals": [...],
        "style": "...",
        "personality": {
            "traits": [...],
            "big_five": {
                "openness": "...",
                "conscientiousness": "...",
                "extraversion": "...",
                "agreeableness": "...",
                "neuroticism": "..."
            }
        },
        "preferences": {
            "interests": [...],
            "likes": [...],
            "dislikes": [...]
        },
        "skills": [...],
        "beliefs": [...],
        "behaviors": {
            "general": [...],
            "routines": {
                "morning": [...],
                "workday": [...],
                "evening": [...],
                "weekend": [...]
            }
        },
        "health": "...",
        "relationships": [...],
        "other_facts": [...]
    }
}
"""


# ============================================================================
# シミュレーション履歴からエージェント別の発言を抽出
# ============================================================================

def extract_agent_section(transcript: str, agent_name: str) -> str:
    """
    トランスクリプトから特定エージェントの視点のセクションを抽出する。
    
    トランスクリプトは "#### Interactions from the point of view of {name} agent:"
    で始まるセクションに分かれている。
    """
    # エージェント名でセクションを検索
    pattern = rf"#### Interactions from the point of view of {re.escape(agent_name)} agent:"
    sections = re.split(r"#### Interactions from the point of view of \w[\w ]+ agent:", transcript)
    headers = re.findall(r"#### Interactions from the point of view of ([\w ]+) agent:", transcript)
    
    for header, section in zip(headers, sections[1:]):  # sections[0]はヘッダー前の空文字
        if header.strip() == agent_name:
            return section.strip()
    
    # セクション分割がうまくいかない場合、全文を返す
    return transcript


# ============================================================================
# LLMによるペルソナ洗練
# ============================================================================

def build_refinement_prompt(
    agent_name: str,
    original_persona: dict,
    transcript: str,
    condition: str,
) -> str:
    """
    ペルソナ洗練用のプロンプトを構築する。
    
    Args:
        agent_name: エージェント名
        original_persona: 元のペルソナJSON (persona フィールドの中身)
        transcript: シミュレーション履歴テキスト
        condition: "autonomous" or "participatory"
    """
    
    condition_context = {
        "autonomous": (
            "This transcript is from an AUTONOMOUS simulation where agents discussed "
            "without any human intervention. Analyze the agent's behavior and identify "
            "areas where the persona definition could be improved to produce more "
            "realistic, productive, and task-appropriate behavior in future simulations."
        ),
        "participatory": (
            "This transcript is from a PARTICIPATORY simulation where a human facilitator "
            "intervened to guide the discussion (e.g., correcting off-topic behavior, "
            "enforcing constraints, requesting more concrete proposals). Analyze how the "
            "agent's behavior changed after human guidance and refine the persona so that "
            "the agent can exhibit this improved behavior AUTONOMOUSLY in future simulations "
            "without needing human intervention."
        ),
    }
    
    prompt = f"""You are an expert in designing personas for LLM-based agent simulations.

## Task
Analyze the simulation transcript below and refine the persona definition for agent "{agent_name}".
{condition_context[condition]}

## Guidelines for Refinement
1. **Preserve identity**: Keep name, age, nationality, gender, residence, education, relationships, and health unchanged.
2. **Refine behavior-related fields**: Focus on improving these fields based on what you observe in the transcript:
   - `occupation.description`: Add role-specific behavioral guidance learned from the simulation
   - `personality.traits`: Add or modify traits that would lead to better simulation behavior
   - `style`: Refine communication style based on observed patterns
   - `behaviors.general`: Add concrete behavioral patterns observed in effective interactions
   - `skills`: Add or refine skills that are relevant to the task
   - `beliefs`: Add beliefs that would guide better decision-making
   - `long_term_goals`: Adjust if the simulation reveals misaligned goals
3. **Be specific**: Replace vague descriptions with concrete, actionable guidance.
4. **Maintain consistency**: Ensure all persona fields remain internally consistent.
5. **Keep the same JSON structure**: The output must have exactly the same fields and nesting as the input.

## Original Persona (JSON)
```json
{json.dumps(original_persona, indent=2, ensure_ascii=False)}
```

## Simulation Transcript
```
{transcript}
```

## Output Instructions
Return ONLY a valid JSON object with the complete refined persona.
The JSON must have exactly the same top-level structure as the original:
{PERSONA_STRUCTURE_DESCRIPTION}

Return the COMPLETE refined persona JSON (not just the changed fields).
Do NOT include any text outside the JSON object.
"""
    return prompt


def refine_persona_with_llm(prompt: str) -> dict:
    """
    LLMを呼び出してペルソナを洗練する。
    
    Args:
        prompt: 洗練用プロンプト
    
    Returns:
        洗練されたペルソナJSON (dict)
    """
    try:
        response = openai.chat.completions.create(
            model=REFINEMENT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert persona designer for LLM-based multi-agent simulations. "
                        "You analyze simulation transcripts and refine agent persona definitions "
                        "to improve future simulation quality. Always output valid JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
        )
        
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    
    except json.JSONDecodeError as e:
        print(f"  ⚠️ JSON解析エラー: {e}")
        # JSONブロックを抽出して再試行
        matches = re.findall(r"\{.*\}", result_text, re.DOTALL)
        for m in reversed(matches):
            try:
                return json.loads(m)
            except Exception:
                continue
        raise ValueError(f"LLMの出力からJSONを解析できませんでした: {result_text[:200]}")
    
    except Exception as e:
        print(f"  ❌ API呼び出しエラー: {e}")
        raise


def validate_refined_persona(original: dict, refined: dict) -> list:
    """
    洗練されたペルソナが元のペルソナと同じ構造を持つか検証する。
    
    Returns:
        警告メッセージのリスト（空なら問題なし）
    """
    warnings = []
    
    # トップレベルキーの確認
    if "persona" not in refined:
        warnings.append("'persona'キーが見つかりません")
        return warnings
    
    orig_persona = original.get("persona", {})
    ref_persona = refined.get("persona", {})
    
    # 不変フィールドの確認
    immutable_fields = ["name", "age", "nationality", "gender", "residence", "education"]
    for field in immutable_fields:
        if orig_persona.get(field) != ref_persona.get(field):
            warnings.append(
                f"不変フィールド '{field}' が変更されています: "
                f"'{orig_persona.get(field)}' → '{ref_persona.get(field)}'"
            )
    
    # 必須フィールドの存在確認
    required_fields = [
        "name", "age", "occupation", "personality", "preferences",
        "skills", "beliefs", "behaviors", "style",
    ]
    for field in required_fields:
        if field not in ref_persona:
            warnings.append(f"必須フィールド '{field}' が欠落しています")
    
    return warnings


# ============================================================================
# ファイル操作
# ============================================================================

def load_persona(path: str) -> dict:
    """ペルソナJSONを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_transcript(path: str) -> str:
    """シミュレーション履歴テキストを読み込む"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def find_transcripts(condition: str) -> list:
    """
    指定条件のシミュレーション履歴ファイルを検索し、
    日付順（新しい順）にソートして返す。
    """
    pattern = os.path.join(SIMULATION_DIR, f"{condition}_*.txt")
    files = glob.glob(pattern)
    files.sort(reverse=True)  # ファイル名に日時が含まれるため降順ソート = 新しい順
    return files


def save_refined_persona(persona: dict, output_path: str):
    """洗練されたペルソナJSONを保存する"""
    outdir = os.path.dirname(output_path)
    if outdir:
        Path(outdir).mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(persona, f, indent=4, ensure_ascii=False)


# ============================================================================
# メイン処理
# ============================================================================

def refine_all_agents(
    condition: str,
    transcript_path: str = None,
    use_all: bool = False,
):
    """
    全エージェントのペルソナを洗練する。
    
    Args:
        condition: "autonomous" or "participatory"
        transcript_path: 特定のトランスクリプトファイルパス（Noneなら最新を使用）
        use_all: Trueなら全トランスクリプトを結合して使用
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        OUTPUT_BASE_DIR, f"refined_from_{condition}_{timestamp}"
    )
    
    print("\n" + "=" * 70)
    print(f"🔄 ペルソナ洗練: {condition}条件のシミュレーション履歴を使用")
    print("=" * 70)
    
    # -----------------------------------------------------------------------
    # トランスクリプトの準備
    # -----------------------------------------------------------------------
    if transcript_path:
        transcripts = [transcript_path]
        print(f"📄 指定トランスクリプト: {transcript_path}")
    else:
        all_transcripts = find_transcripts(condition)
        if not all_transcripts:
            print(f"❌ {condition}条件のシミュレーション履歴が見つかりません")
            return
        
        if use_all:
            transcripts = all_transcripts
            print(f"📄 全{len(transcripts)}件のトランスクリプトを結合して使用")
        else:
            transcripts = [all_transcripts[0]]  # 最新1件
            print(f"📄 最新トランスクリプト: {transcripts[0]}")
    
    # トランスクリプトを読み込んで結合
    combined_transcript = ""
    for tp in transcripts:
        content = load_transcript(tp)
        combined_transcript += f"\n\n--- Transcript: {os.path.basename(tp)} ---\n\n"
        combined_transcript += content
    
    print(f"📝 トランスクリプト合計文字数: {len(combined_transcript):,}")
    
    # -----------------------------------------------------------------------
    # 各エージェントについて洗練を実行
    # -----------------------------------------------------------------------
    results = {}
    
    for agent_name, spec_path in AGENT_SPECS.items():
        print(f"\n{'─' * 50}")
        print(f"🧑 {agent_name} のペルソナを洗練中...")
        print(f"{'─' * 50}")
        
        # 元のペルソナを読み込む
        original = load_persona(spec_path)
        original_persona = original.get("persona", {})
        
        # エージェント別のトランスクリプトセクションを抽出
        agent_transcript = extract_agent_section(combined_transcript, agent_name)
        print(f"  📄 抽出されたトランスクリプト: {len(agent_transcript):,} 文字")
        
        # 洗練用プロンプトを構築
        prompt = build_refinement_prompt(
            agent_name=agent_name,
            original_persona=original_persona,
            transcript=agent_transcript,
            condition=condition,
        )
        print(f"  📋 プロンプト長: {len(prompt):,} 文字")
        
        # LLMで洗練
        print(f"  🤖 LLM ({REFINEMENT_MODEL}) で洗練を実行中...")
        refined = refine_persona_with_llm(prompt)
        
        # 検証
        warnings = validate_refined_persona(original, refined)
        if warnings:
            print(f"  ⚠️ 検証警告:")
            for w in warnings:
                print(f"     - {w}")
            # 不変フィールドが変更されていた場合、元の値で上書き
            if "persona" in refined:
                immutable_fields = [
                    "name", "age", "nationality", "gender",
                    "residence", "education", "health", "relationships",
                ]
                for field in immutable_fields:
                    if field in original_persona:
                        refined["persona"][field] = original_persona[field]
                print(f"  ✅ 不変フィールドを元の値で復元しました")
        else:
            print(f"  ✅ 検証OK: 構造が一致しています")
        
        # トップレベルフィールドの保持
        if "type" not in refined:
            refined["type"] = original.get("type", "TinyPerson")
        if "current_episode_event_count" not in refined:
            refined["current_episode_event_count"] = original.get("current_episode_event_count", 0)
        if "mental_faculties" not in refined:
            refined["mental_faculties"] = original.get("mental_faculties", [])
        
        # 保存
        # ファイル名は元のファイル名と同じにする
        output_filename = os.path.basename(spec_path)
        output_path = os.path.join(output_dir, output_filename)
        save_refined_persona(refined, output_path)
        print(f"  💾 保存先: {output_path}")
        
        # 変更点のサマリーを表示
        show_diff_summary(original_persona, refined.get("persona", {}))
        
        results[agent_name] = {
            "original_path": spec_path,
            "refined_path": output_path,
            "warnings": warnings,
        }
    
    # -----------------------------------------------------------------------
    # メタデータの保存
    # -----------------------------------------------------------------------
    metadata = {
        "timestamp": timestamp,
        "condition": condition,
        "model": REFINEMENT_MODEL,
        "temperature": TEMPERATURE,
        "transcripts_used": [os.path.basename(tp) for tp in transcripts],
        "agents": results,
    }
    metadata_path = os.path.join(output_dir, "_refinement_metadata.json")
    save_refined_persona(metadata, metadata_path)
    
    print(f"\n{'=' * 70}")
    print(f"✅ 全エージェントの洗練が完了しました")
    print(f"   出力ディレクトリ: {output_dir}")
    print(f"   メタデータ: {metadata_path}")
    print(f"{'=' * 70}")
    
    return output_dir


def show_diff_summary(original_persona: dict, refined_persona: dict):
    """
    ペルソナの変更箇所のサマリーを表示する。
    """
    diff_fields = []
    
    # 比較対象フィールド
    check_fields = [
        "occupation.description",
        "style",
        "long_term_goals",
    ]
    
    # occupation.description
    orig_desc = original_persona.get("occupation", {}).get("description", "")
    ref_desc = refined_persona.get("occupation", {}).get("description", "")
    if orig_desc != ref_desc:
        diff_fields.append("occupation.description")
    
    # style
    if original_persona.get("style") != refined_persona.get("style"):
        diff_fields.append("style")
    
    # long_term_goals
    if original_persona.get("long_term_goals") != refined_persona.get("long_term_goals"):
        diff_fields.append("long_term_goals")
    
    # personality.traits
    orig_traits = original_persona.get("personality", {}).get("traits", [])
    ref_traits = refined_persona.get("personality", {}).get("traits", [])
    if orig_traits != ref_traits:
        diff_fields.append(f"personality.traits ({len(orig_traits)}→{len(ref_traits)} items)")
    
    # behaviors.general
    orig_beh = original_persona.get("behaviors", {}).get("general", [])
    ref_beh = refined_persona.get("behaviors", {}).get("general", [])
    if orig_beh != ref_beh:
        diff_fields.append(f"behaviors.general ({len(orig_beh)}→{len(ref_beh)} items)")
    
    # skills
    orig_skills = original_persona.get("skills", [])
    ref_skills = refined_persona.get("skills", [])
    if orig_skills != ref_skills:
        diff_fields.append(f"skills ({len(orig_skills)}→{len(ref_skills)} items)")
    
    # beliefs
    orig_beliefs = original_persona.get("beliefs", [])
    ref_beliefs = refined_persona.get("beliefs", [])
    if orig_beliefs != ref_beliefs:
        diff_fields.append(f"beliefs ({len(orig_beliefs)}→{len(ref_beliefs)} items)")
    
    if diff_fields:
        print(f"  📊 変更されたフィールド:")
        for field in diff_fields:
            print(f"     - {field}")
    else:
        print(f"  📊 変更なし（元のペルソナと同一）")


# ============================================================================
# コマンドラインインターフェース
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="シミュレーション履歴に基づくペルソナ洗練スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 参加型履歴の最新1件から洗練
  python refine_persona.py --condition participatory

  # 自律型履歴の全件を結合して洗練
  python refine_persona.py --condition autonomous --use-all

  # 特定のトランスクリプトを指定して洗練
  python refine_persona.py --condition participatory --transcript simulation_results/participatory_20260126_190642.txt
        """,
    )
    
    parser.add_argument(
        "--condition",
        type=str,
        required=True,
        choices=["autonomous", "participatory"],
        help="洗練に使用するシミュレーション条件",
    )
    parser.add_argument(
        "--transcript",
        type=str,
        default=None,
        help="特定のトランスクリプトファイルパス（省略時は最新を使用）",
    )
    parser.add_argument(
        "--use-all",
        action="store_true",
        default=False,
        help="全トランスクリプトを結合して使用（デフォルトは最新1件のみ）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"使用するLLMモデル（デフォルト: {REFINEMENT_MODEL}）",
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # モデルの上書き
    global REFINEMENT_MODEL
    if args.model:
        REFINEMENT_MODEL = args.model
    
    print(f"\n{'=' * 70}")
    print(f"🧪 ペルソナ洗練パイプライン")
    print(f"{'=' * 70}")
    print(f"  条件:       {args.condition}")
    print(f"  モデル:     {REFINEMENT_MODEL}")
    print(f"  温度:       {TEMPERATURE}")
    print(f"  全件使用:   {args.use_all}")
    print(f"  開始時刻:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    output_dir = refine_all_agents(
        condition=args.condition,
        transcript_path=args.transcript,
        use_all=args.use_all,
    )
    
    if output_dir:
        print(f"\n💡 洗練されたペルソナで自律シミュレーションを実行するには:")
        print(f"   run_autonomous_only.py の SPEC_PATH を以下に変更してください:")
        print(f"   PM_SPEC_PATH = \"{output_dir}/pm_participatory.json\"")
        print(f"   ENGINEER_SPEC_PATH = \"{output_dir}/engineer_participatory.json\"")
        print(f"   AI_RESEARCHER_SPEC_PATH = \"{output_dir}/ai_researcher_participatory.json\"")
    
    print(f"\n✅ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

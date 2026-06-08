# ========== micro_evaluation.py ==========
"""
ミクロ評価モジュール (LLM-as-a-judge)

エージェント個別の行動品質を評価する。
evaluation.md に基づく3つの指標:
- Persona Consistency: 役割に沿った行動か
- Logical Consistency: 矛盾のない推論か
- Task Adherence: 議題に沿った発話か
"""

import openai
import json
import logging
import numpy as np
from typing import List, Dict, Any

from tinytroupe.agent import TinyPerson

logger = logging.getLogger("tinytroupe.evaluation")


class MicroEvaluator:
    """
    エージェント個別の行動品質を評価 (LLM-as-a-judge)
    
    evaluation.md の RQ1 に対応:
    "Human feedback はエージェント行動の品質を向上させるか？"
    """
    
    def __init__(self, model: str = "gpt-4o"):
        """
        Args:
            model: 評価に使用するモデル (論文ではGPT-4oを推奨)
        """
        self.model = model
        self.client = openai.OpenAI()
    
    def evaluate_single_action(self, 
                               action: dict, 
                               agent_role: str, 
                               meeting_topic: str,
                               previous_context: List[str]) -> Dict[str, Any]:
        """
        単一の行動を評価
        
        Args:
            action: エージェントの行動 {"type": "TALK", "content": "..."}
            agent_role: エージェントの役割説明
            meeting_topic: 会議の議題
            previous_context: 直前の文脈（最近の発話）
        
        Returns:
            dict: 評価スコア
        """
        
        prompt = f"""
You are a STRICT evaluator for multi-agent meeting simulations.
You must be rigorous and critical. Start from a maximum score and DEDUCT points for each flaw found.

# Agent Information
- Role: {agent_role}

# Meeting Topic
{meeting_topic}

# Recent Context (last 3 actions)
{chr(10).join([f"- {ctx}" for ctx in previous_context[-3:]]) if previous_context else "(No previous context)"}

# Action to Evaluate
Type: {action.get('type')}
Content: {action.get('content')}

# STRICT Evaluation Criteria (Deduction-Based Scoring)

For EACH criterion, start at 5 and apply deductions:

## 1. Persona Consistency (persona_consistency)
Does this action align with the agent's assigned role?

**Deduction Rules:**
- Action could be said by anyone (not role-specific): -1
- Uses expertise outside assigned role: -1 to -2
- Contradicts role responsibilities: -2
- Completely ignores role (e.g., PM discussing technical implementation details that should be engineer's job): -3

**Score Bands:**
- 5: Perfect - Action clearly reflects role expertise and responsibilities
- 4: Good - Minor deviation but generally role-appropriate
- 3: Acceptable - Generic action, not leveraging role
- 2: Poor - Role confusion or inappropriate scope
- 1: Unacceptable - Complete role violation

## 2. Logical Consistency (logical_consistency)
Is this action logically coherent with previous statements?

**Deduction Rules:**
- Repeating similar ideas without progression: -1
- Minor inconsistency with earlier statement: -1
- Ignoring relevant context from previous actions: -1
- Direct contradiction with own previous statement: -2
- Direct contradiction with agreed decisions: -3

**Score Bands:**
- 5: Perfect - Builds logically on previous context
- 4: Good - Coherent with minor gaps
- 3: Acceptable - Some logical jumps or repetition
- 2: Poor - Noticeable contradictions
- 1: Unacceptable - Major contradictions or incoherence

## 3. Task Adherence (task_adherence)
Does this action stay on topic and contribute to meeting goals?

**Deduction Rules:**
- Vague/abstract statement without specifics: -1
- Generic filler ("I agree", "That sounds good" without substance): -1
- Does not advance meeting goals: -1
- Partial digression from topic: -1 to -2
- Complete off-topic digression: -3

**Score Bands:**
- 5: Perfect - Specific, actionable contribution to meeting goals
- 4: Good - On-topic with minor vagueness
- 3: Acceptable - Relevant but not advancing goals
- 2: Poor - Mostly vague or partially off-topic
- 1: Unacceptable - Off-topic or no contribution

# IMPORTANT RULES
1. **When in doubt, choose the LOWER score.** Be harsh, not lenient.
2. **If contradictions exist, adopt the WORST interpretation.**
3. **Average meeting action should score around 3.** Only give 4+ for genuinely good actions.
4. **Score 5 is RARE** - reserved for specific, actionable, role-appropriate contributions.
5. **Provide SPECIFIC justification** - cite exact phrases or issues, not vague statements.

# Output Format
Respond with ONLY a JSON object (no markdown):
{{
    "persona_consistency": <1-5>,
    "persona_deductions": "List specific deductions applied (e.g., '-1: generic statement')",
    "logical_consistency": <1-5>,
    "logical_deductions": "List specific deductions applied",
    "task_adherence": <1-5>,
    "task_deductions": "List specific deductions applied",
    "reasoning": "Overall assessment citing specific issues or strengths"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a STRICT and RIGOROUS evaluator for multi-agent simulations. You must be critical and apply deductions for every flaw found. When in doubt, assign LOWER scores. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating action: {e}")
            return {
                "persona_consistency": 3,
                "logical_consistency": 3,
                "task_adherence": 3,
                "reasoning": f"Evaluation failed: {str(e)}",
                "error": True
            }
    
    def evaluate_agent_actions(self, 
                               agent: TinyPerson,
                               meeting_topic: str,
                               sample_size: int = None) -> Dict[str, Any]:
        """
        エージェントの行動履歴を評価
        
        Args:
            agent: 評価対象のエージェント
            meeting_topic: 会議の議題
            sample_size: 評価するアクション数 (Noneなら全て)
        
        Returns:
            dict: 平均スコアと詳細評価
        """
        # エージェントの役割を取得
        occupation = agent.get("occupation")
        if isinstance(occupation, dict):
            agent_role = occupation.get("description", occupation.get("title", "Unknown"))
        else:
            agent_role = str(occupation) if occupation else "Unknown"
        
        # 行動履歴を取得
        actions = agent.episodic_memory.retrieve_all(item_type="action")
        
        # アクションを抽出するヘルパー関数
        def extract_action(record):
            """エピソディックメモリのレコードからアクションを抽出"""
            # 新形式: {'role': 'assistant', 'content': {'action': {...}}, 'type': 'action'}
            content = record.get('content', {})
            if isinstance(content, dict):
                return content.get('action', {})
            # 旧形式: {'action': {...}}
            return record.get('action', {})
        
        # TALK/THINKアクションのみをフィルタ
        talk_actions = [a for a in actions if extract_action(a).get('type') in ['TALK', 'THINK']]
        
        # サンプリング
        if sample_size and len(talk_actions) > sample_size:
            # 均等にサンプリング
            indices = np.linspace(0, len(talk_actions) - 1, sample_size, dtype=int)
            talk_actions = [talk_actions[i] for i in indices]
        
        evaluations = []
        previous_context = []
        
        for i, action_record in enumerate(talk_actions):
            action = extract_action(action_record)
            
            eval_result = self.evaluate_single_action(
                action=action,
                agent_role=agent_role,
                meeting_topic=meeting_topic,
                previous_context=previous_context
            )
            
            eval_result["action_index"] = i
            eval_result["action_type"] = action.get('type')
            eval_result["action_content"] = action.get('content', '')[:200]  # 最初の200文字
            evaluations.append(eval_result)
            
            # 文脈を更新
            previous_context.append(f"{action.get('type')}: {action.get('content', '')[:100]}")
            if len(previous_context) > 5:
                previous_context.pop(0)
        
        # 平均スコア計算
        if evaluations:
            avg_scores = {
                "persona_consistency": np.mean([e["persona_consistency"] for e in evaluations if "persona_consistency" in e]),
                "logical_consistency": np.mean([e["logical_consistency"] for e in evaluations if "logical_consistency" in e]),
                "task_adherence": np.mean([e["task_adherence"] for e in evaluations if "task_adherence" in e])
            }
            
            # 標準偏差も計算
            std_scores = {
                "persona_consistency_std": np.std([e["persona_consistency"] for e in evaluations if "persona_consistency" in e]),
                "logical_consistency_std": np.std([e["logical_consistency"] for e in evaluations if "logical_consistency" in e]),
                "task_adherence_std": np.std([e["task_adherence"] for e in evaluations if "task_adherence" in e])
            }
        else:
            avg_scores = {"persona_consistency": 0, "logical_consistency": 0, "task_adherence": 0}
            std_scores = {"persona_consistency_std": 0, "logical_consistency_std": 0, "task_adherence_std": 0}
        
        return {
            "agent_name": agent.name,
            "agent_role": agent_role,
            "average_scores": avg_scores,
            "std_scores": std_scores,
            "detailed_evaluations": evaluations,
            "total_actions_evaluated": len(evaluations)
        }
    
    def evaluate_multiple_agents(self, 
                                 agents: List[TinyPerson],
                                 meeting_topic: str,
                                 sample_size_per_agent: int = 5) -> Dict[str, Any]:
        """
        複数エージェントを評価
        
        Args:
            agents: 評価対象のエージェントリスト
            meeting_topic: 会議の議題
            sample_size_per_agent: 各エージェントから評価するアクション数
        
        Returns:
            dict: 全体の評価結果
        """
        results = []
        
        for agent in agents:
            result = self.evaluate_agent_actions(
                agent=agent,
                meeting_topic=meeting_topic,
                sample_size=sample_size_per_agent
            )
            results.append(result)
            logger.info(f"Evaluated {agent.name}: {result['average_scores']}")
        
        # 全体平均を計算
        all_scores = {
            "persona_consistency": [],
            "logical_consistency": [],
            "task_adherence": []
        }
        
        for r in results:
            for metric in all_scores.keys():
                if metric in r["average_scores"]:
                    all_scores[metric].append(r["average_scores"][metric])
        
        overall_average = {
            metric: np.mean(scores) if scores else 0
            for metric, scores in all_scores.items()
        }
        
        overall_std = {
            f"{metric}_std": np.std(scores) if scores else 0
            for metric, scores in all_scores.items()
        }
        
        return {
            "agents": results,
            "overall_average": overall_average,
            "overall_std": overall_std,
            "total_agents": len(agents)
        }


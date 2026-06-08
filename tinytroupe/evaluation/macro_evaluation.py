# ========== macro_evaluation.py ==========
"""
マクロ評価モジュール (ハイブリッド: ResultsExtractor + LLM-as-a-judge)

シミュレーション全体の成果を評価する。
evaluation.md に基づく指標:
- 合意形成成功率
- 成果物の質 (5つの観点)
- 技術矛盾の発生数

成果物の抽出にはResultsExtractorを使用し、
品質評価には外部LLM (LLM-as-a-judge) を使用する。
"""

import openai
import json
import logging
from typing import Dict, Any, List

from tinytroupe.extraction import ResultsExtractor
from tinytroupe.environment import TinyWorld
from .deliverables import REQUIRED_DELIVERABLES

logger = logging.getLogger("tinytroupe.evaluation")


class MacroEvaluator:
    """
    シミュレーション全体の成果を評価 (ハイブリッド方式)
    
    evaluation.md の RQ2 に対応:
    "自律シミュレーションと参加型シミュレーションでは結果がどのように異なるか？"
    """
    
    def __init__(self, model: str = "gpt-4o"):
        """
        Args:
            model: 品質評価に使用するモデル
        """
        self.model = model
        self.client = openai.OpenAI()
        
        # 成果物抽出用のResultsExtractor
        self.deliverables_extractor = ResultsExtractor(
            extraction_objective="Extract the final deliverables from the meeting discussion",
            fields=list(REQUIRED_DELIVERABLES.keys()),
            fields_hints={
                k: v["description"] for k, v in REQUIRED_DELIVERABLES.items()
            }
        )
    
    def extract_deliverables(self, world: TinyWorld) -> Dict[str, Any]:
        """
        会議から成果物を抽出 (ResultsExtractor使用)
        
        Args:
            world: 会議ワールド
        
        Returns:
            dict: 抽出された成果物
        """
        result = self.deliverables_extractor.extract_results_from_world(
            world,
            situation="This is a meeting to design a smart lab demo system for open campus. Extract what was decided for each deliverable."
        )
        
        return result
    
    def evaluate_deliverables_quality(self, 
                                      transcript: str,
                                      deliverables: Dict[str, Any]) -> Dict[str, Any]:
        """
        成果物の質を評価 (LLM-as-a-judge)
        
        Args:
            transcript: 会議のトランスクリプト
            deliverables: 抽出された成果物
        
        Returns:
            dict: 各成果物の評価スコア
        """
        prompt = f"""
You are a STRICT and RIGOROUS evaluator for meeting outcomes. 
You must be critical and apply deductions for every flaw found. When in doubt, assign LOWER scores.

# Meeting Transcript (Summary)
{transcript[:5000]}

# Extracted Deliverables
{json.dumps(deliverables, indent=2, ensure_ascii=False)}

# Required Deliverables and Their Required Elements
{json.dumps(REQUIRED_DELIVERABLES, indent=2, ensure_ascii=False)}

# STRICT Evaluation Criteria (Deduction-Based Scoring)

For EACH deliverable, evaluate on 5 dimensions. Start at 5 and DEDUCT for each flaw:

## Universal Deduction Rules (apply to ALL deliverables)
- Vague/abstract without specifics: -1 per instance
- Missing required element: -1 per missing element
- Generic terms instead of specifics (e.g., "sensors" vs "DHT22"): -1
- No actionable details: -1
- Contradictions or inconsistencies: -2
- Complete absence of deliverable: Score 1 automatically

## Deliverable-Specific Criteria

### 1. central_concept (Demo Theme)
- 5: Named concept with tagline, clear purpose, defined target audience, stated uniqueness
- 4: Clear concept but missing one element (e.g., no tagline)
- 3: General idea only (e.g., "Smart Lab showcase")
- 2: Only technology mentioned, no cohesive concept
- 1: No concept or completely unclear

### 2. experience_flow (Visitor Experience)
- 5: Step-by-step with SPECIFIC durations (e.g., "3 min intro, 7 min demo, 2 min Q&A")
- 4: Clear phases but missing specific times
- 3: General flow ("intro, demo, conclusion") without details
- 2: Vague mentions only
- 1: No flow defined

### 3. technical_architecture (Technical Configuration)
- 5: SPECIFIC device models (e.g., "Raspberry Pi 4", "DHT22"), exact LLM model (e.g., "GPT-4"), MCP tools named, integration method described
- 4: Most specifics present but missing one component
- 3: Generic terms ("sensors", "AI", "IoT devices")
- 2: High-level categories only
- 1: No technical details

### 4. role_assignment (Role Division)
- 5: Named individuals with SPECIFIC tasks and DEADLINES (e.g., "Daniel: sensor setup by Jan 20")
- 4: Specific tasks to named people but no deadlines
- 3: General roles ("engineer handles hardware")
- 2: Job titles only
- 1: No assignment

### 5. required_resources (Resources)
- 5: QUANTITIES and BUDGET estimates (e.g., "2x Raspberry Pi @ $100, 3 person-days")
- 4: Items with quantities OR budget (not both)
- 3: General categories ("hardware, time, people")
- 2: Only "existing resources" or "minimal budget"
- 1: No resources discussed

# IMPORTANT RULES
1. **When in doubt, choose the LOWER score.** Be harsh, not lenient.
2. **If contradictions exist, adopt the WORST interpretation.**
3. **Average meeting should score 2-3.** Only give 4+ for genuinely specific deliverables.
4. **Score 5 is RARE** - requires ALL required elements with concrete specifics.
5. **Provide SPECIFIC justification** - cite what is missing or vague, not general statements.

# Output Format
Respond with ONLY a JSON object:
{{
    "central_concept": {{
        "completeness": <1-5>,
        "concreteness": <1-5>,
        "feasibility": <1-5>,
        "consistency": <1-5>,
        "innovation": <1-5>,
        "overall": <1-5>,
        "deductions": "List specific deductions (e.g., '-1: no tagline, -1: vague purpose')",
        "comments": "Cite SPECIFIC missing elements or vague phrases"
    }},
    "experience_flow": {{ ... same structure ... }},
    "technical_architecture": {{ ... same structure ... }},
    "role_assignment": {{ ... same structure ... }},
    "required_resources": {{ ... same structure ... }},
    "overall_quality": <1-5>,
    "overall_deductions": "Summary of major issues across all deliverables",
    "overall_comments": "Critical assessment - what concrete details are missing?"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a STRICT and RIGOROUS evaluator for meeting outcomes. You must be critical and apply deductions for every flaw found. When in doubt, assign LOWER scores. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating deliverables quality: {e}")
            return {"error": str(e), "overall_quality": 0}
    
    def detect_contradictions(self, transcript: str) -> Dict[str, Any]:
        """
        会議中の矛盾を検出 (LLM使用)
        
        Args:
            transcript: 会議のトランスクリプト
        
        Returns:
            dict: 検出された矛盾のリストと統計
        """
        prompt = f"""
Analyze this meeting transcript for contradictions.

A contradiction is when:
1. Two statements directly oppose each other
2. A speaker contradicts their own earlier statement
3. An agreed decision is later overturned without acknowledgment

# Meeting Transcript
{transcript[:8000]}

# Output Format
Respond with ONLY a JSON object:
{{
    "contradictions": [
        {{
            "statement_1": "First conflicting statement",
            "statement_2": "Second conflicting statement",
            "speakers": ["Speaker1", "Speaker2"],
            "severity": "low|medium|high",
            "explanation": "Brief explanation"
        }}
    ],
    "total_count": <number>,
    "high_severity_count": <number>,
    "summary": "Overall assessment of logical consistency"
}}

If no contradictions found, return empty array for contradictions.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at detecting logical contradictions in discussions. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # 必要なフィールドを確保
            if "contradictions" not in result:
                result["contradictions"] = []
            if "total_count" not in result:
                result["total_count"] = len(result["contradictions"])
            if "high_severity_count" not in result:
                result["high_severity_count"] = sum(
                    1 for c in result["contradictions"] 
                    if c.get("severity") == "high"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting contradictions: {e}")
            return {
                "contradictions": [],
                "total_count": 0,
                "high_severity_count": 0,
                "error": str(e)
            }
    
    def check_consensus_success(self, deliverables: Dict[str, Any]) -> Dict[str, Any]:
        """
        合意形成が成功したかチェック (LLM使用)
        
        Args:
            deliverables: 抽出された成果物
        
        Returns:
            dict: 成功判定と理由
        """
        # NOTE: Removed upfront key-existence / truthiness check per design decision.
        # Always run the LLM-based consensus judgment, and fall back to a simple
        # presence-based fallback only if the LLM call fails.
        
        # LLMで質をチェック
        prompt = f"""
Evaluate whether this meeting achieved successful consensus.

# Deliverables
{json.dumps(deliverables, indent=2, ensure_ascii=False)}

# Required Deliverables
{json.dumps({k: v["description"] for k, v in REQUIRED_DELIVERABLES.items()}, indent=2, ensure_ascii=False)}

# Success Criteria
- All required items are present
- Each item is specific and actionable
- No major gaps or undefined areas

# Output Format
Respond with ONLY a JSON object:
{{
    "success": true/false,
    "completeness_rate": <0.0-1.0>,
    "reason": "Explanation of judgment",
    "weak_areas": ["area1", "area2"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at evaluating meeting outcomes. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error checking consensus success: {e}")
            # フォールバック: LLMが利用できない場合は deliverables が存在するかどうかで簡易判定
            return {
                "success": bool(deliverables),
                "completeness_rate": 1.0 if bool(deliverables) else 0.0,
                "reason": "Fallback: LLM error, presence-based simple fallback applied",
                "error": str(e)
            }
    
    def evaluate_full(self, world: TinyWorld) -> Dict[str, Any]:
        """
        シミュレーション全体のマクロ評価を実行
        
        Args:
            world: 会議ワールド
        
        Returns:
            dict: 完全な評価結果
        """
        # トランスクリプト取得
        transcript = world.pretty_current_interactions(
            max_content_length=None,
            first_n=None,
            last_n=None
        )
        
        # 1. 成果物を抽出
        logger.info("Extracting deliverables...")
        deliverables = self.extract_deliverables(world)
        
        # 2. 成果物の質を評価
        logger.info("Evaluating deliverables quality...")
        quality = self.evaluate_deliverables_quality(transcript, deliverables)
        
        # 3. 矛盾を検出
        logger.info("Detecting contradictions...")
        contradictions = self.detect_contradictions(transcript)
        
        # 4. 合意形成成功判定
        logger.info("Checking consensus success...")
        consensus = self.check_consensus_success(deliverables)
        
        return {
            "deliverables": deliverables,
            "deliverables_quality": quality,
            "contradictions": contradictions,
            "consensus": consensus,
            "summary": {
                "consensus_success": consensus.get("success", False),
                "overall_quality": quality.get("overall_quality", 0),
                "contradiction_count": contradictions.get("total_count", 0),
                "completeness_rate": consensus.get("completeness_rate", 0)
            }
        }

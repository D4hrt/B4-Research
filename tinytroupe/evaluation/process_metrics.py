# ========== process_metrics.py ==========
"""
プロセス指標モジュール (LLM不使用)

シミュレーションのプロセスに関する定量的指標を計算する。
LLMを使用せず、純粋な計算で測定可能な指標:
- ターン数
- 停滞率 (類似発話の連続)
- 発散回数 (議題から逸れた発話)
"""

import logging
import numpy as np
from typing import Dict, Any, List

from tinytroupe.environment import TinyWorld
from tinytroupe import openai_utils

logger = logging.getLogger("tinytroupe.evaluation")


class ProcessMetrics:
    """
    プロセス指標を計算 (LLM不使用)
    
    evaluation.md のマクロ評価指標のうち、
    LLMを使わずに計算可能なものを担当:
    - 成功までのターン数
    - 議論の停滞率
    - 発散回数
    """
    
    def __init__(self, 
                 stagnation_threshold: float = 0.85,
                 divergence_threshold: float = 0.3):
        """
        Args:
            stagnation_threshold: 停滞とみなす類似度の閾値
            divergence_threshold: 発散とみなす類似度の閾値（議題との類似度がこれ以下）
        """
        self.stagnation_threshold = stagnation_threshold
        self.divergence_threshold = divergence_threshold
    
    def count_turns(self, world: TinyWorld) -> int:
        """
        総ターン数をカウント
        
        Args:
            world: 会議ワールド
        
        Returns:
            int: ターン数
        """
        return len(world._displayed_communications_buffer)
    
    def extract_talks(self, world: TinyWorld) -> List[str]:
        """
        発話を抽出
        
        Args:
            world: 会議ワールド
        
        Returns:
            List[str]: 発話リスト
        """
        interactions = world.pretty_current_interactions(
            max_content_length=None,
            first_n=None,
            last_n=None
        )
        
        # TALK/THINKを含む行を抽出
        talks = [
            line.strip() for line in interactions.split('\n')
            if ('TALK' in line or 'THINK' in line) and line.strip()
        ]
        
        return talks
    
    def calculate_stagnation_rate(self, world: TinyWorld) -> Dict[str, Any]:
        """
        議論の停滞率を計算
        
        停滞 = 連続する発話間の類似度が高い状態
        
        Args:
            world: 会議ワールド
        
        Returns:
            dict: 停滞率と詳細情報
        """
        talks = self.extract_talks(world)
        
        if len(talks) < 2:
            return {
                "stagnation_rate": 0.0,
                "stagnation_count": 0,
                "total_transitions": 0,
                "average_similarity": 0.0
            }
        
        try:
            # 埋め込みベクトルを取得
            embeddings = []
            for talk in talks:
                emb = openai_utils.client().get_embedding(talk)
                embeddings.append(emb)
            
            # 連続する発話間の類似度を計算
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = np.dot(embeddings[i], embeddings[i+1]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1]) + 1e-8
                )
                similarities.append(sim)
            
            # 高類似度（停滞）の割合
            stagnation_count = sum(
                1 for sim in similarities 
                if sim > self.stagnation_threshold
            )
            
            return {
                "stagnation_rate": stagnation_count / len(similarities) if similarities else 0.0,
                "stagnation_count": stagnation_count,
                "total_transitions": len(similarities),
                "average_similarity": np.mean(similarities) if similarities else 0.0,
                "max_similarity": max(similarities) if similarities else 0.0,
                "min_similarity": min(similarities) if similarities else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating stagnation rate: {e}")
            return {
                "stagnation_rate": 0.0,
                "stagnation_count": 0,
                "total_transitions": 0,
                "error": str(e)
            }
    
    def calculate_divergence_count(self, 
                                   world: TinyWorld, 
                                   meeting_topic: str) -> Dict[str, Any]:
        """
        発散回数を計算
        
        発散 = 議題との類似度が低い発話
        
        Args:
            world: 会議ワールド
            meeting_topic: 会議の議題
        
        Returns:
            dict: 発散回数と詳細情報
        """
        talks = self.extract_talks(world)
        
        if not talks:
            return {
                "divergence_count": 0,
                "divergence_rate": 0.0,
                "total_talks": 0
            }
        
        try:
            # 議題の埋め込みを取得
            topic_embedding = openai_utils.client().get_embedding(meeting_topic)
            topic_norm = np.linalg.norm(topic_embedding)
            
            # 各発話と議題の類似度を計算
            divergent_talks = []
            similarities = []
            
            for i, talk in enumerate(talks):
                talk_embedding = openai_utils.client().get_embedding(talk)
                talk_norm = np.linalg.norm(talk_embedding)
                
                similarity = np.dot(topic_embedding, talk_embedding) / (topic_norm * talk_norm + 1e-8)
                similarities.append(similarity)
                
                if similarity < self.divergence_threshold:
                    divergent_talks.append({
                        "index": i,
                        "talk": talk[:100],  # 最初の100文字
                        "similarity": similarity
                    })
            
            return {
                "divergence_count": len(divergent_talks),
                "divergence_rate": len(divergent_talks) / len(talks) if talks else 0.0,
                "total_talks": len(talks),
                "average_topic_similarity": np.mean(similarities) if similarities else 0.0,
                "divergent_examples": divergent_talks[:5]  # 最初の5件のみ
            }
            
        except Exception as e:
            logger.error(f"Error calculating divergence count: {e}")
            return {
                "divergence_count": 0,
                "divergence_rate": 0.0,
                "total_talks": len(talks),
                "error": str(e)
            }
    
    def calculate_turn_efficiency(self, 
                                   world: TinyWorld, 
                                   macro_consensus_success: bool,
                                   macro_completeness_rate: float = 0.0,
                                   macro_weak_areas: List[str] = None) -> Dict[str, Any]:
        """
        ターン効率を計算（MacroEvaluatorの合意形成判定を使用）
        
        合意形成の判定は MacroEvaluator のLLMベース判定を使用し、
        ProcessMetrics は効率性指標の計算のみを担当する。
        
        Args:
            world: 会議ワールド
            macro_consensus_success: MacroEvaluatorからの合意形成成功フラグ
            macro_completeness_rate: MacroEvaluatorからの完了率
            macro_weak_areas: MacroEvaluatorからの弱点領域
        
        Returns:
            dict: ターン効率情報
        """
        talks = self.extract_talks(world)
        total_turns = len(talks)
        
        if total_turns == 0:
            return {
                "consensus_achieved": macro_consensus_success,
                "total_turns": 0,
                "efficiency_ratio": 0.0,
                "completeness_rate": macro_completeness_rate,
                "weak_areas": macro_weak_areas or [],
                "note": "No turns recorded"
            }
        
        # MacroEvaluatorの結果を使用して合意形成を判定
        if macro_consensus_success:
            # 合意形成成功: 効率は全ターン数に対する比率
            # 本来は「いつ合意に達したか」を測りたいが、
            # シミュレーション終了時に評価するため最終ターン=合意ターンとみなす
            efficiency_ratio = 1.0  # 全ターン使って合意達成
        else:
            efficiency_ratio = 0.0  # 合意未達成
        
        return {
            "consensus_achieved": macro_consensus_success,
            "total_turns": total_turns,
            "efficiency_ratio": efficiency_ratio,
            "completeness_rate": macro_completeness_rate,
            "weak_areas": macro_weak_areas or [],
            "note": "Consensus judgment based on MacroEvaluator (LLM-based)"
        }
    
    def calculate_all_metrics(self, 
                              world: TinyWorld,
                              meeting_topic: str,
                              macro_consensus_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        全てのプロセス指標を計算
        
        Args:
            world: 会議ワールド
            meeting_topic: 会議の議題
            macro_consensus_result: MacroEvaluatorからの合意形成判定結果
                                   {"success": bool, "completeness_rate": float, "weak_areas": list}
        
        Returns:
            dict: 全プロセス指標
        """
        logger.info("Calculating process metrics...")
        
        # ターン数
        turns = self.count_turns(world)
        logger.info(f"  Turns: {turns}")
        
        # 停滞率
        stagnation = self.calculate_stagnation_rate(world)
        logger.info(f"  Stagnation rate: {stagnation['stagnation_rate']:.2%}")
        
        # 発散回数
        divergence = self.calculate_divergence_count(world, meeting_topic)
        logger.info(f"  Divergence count: {divergence['divergence_count']}")
        
        # MacroEvaluatorの結果を使用してターン効率を計算
        if macro_consensus_result:
            consensus_info = self.calculate_turn_efficiency(
                world=world,
                macro_consensus_success=macro_consensus_result.get("success", False),
                macro_completeness_rate=macro_consensus_result.get("completeness_rate", 0.0),
                macro_weak_areas=macro_consensus_result.get("weak_areas", [])
            )
            logger.info(f"  Consensus achieved (via MacroEvaluator): {consensus_info['consensus_achieved']}")
        else:
            # 後方互換性のため、MacroEvaluatorの結果がない場合は未達成とする
            logger.warning("  MacroEvaluator result not provided - consensus assumed as not achieved")
            consensus_info = {
                "consensus_achieved": False,
                "total_turns": turns,
                "efficiency_ratio": 0.0,
                "completeness_rate": 0.0,
                "weak_areas": [],
                "note": "MacroEvaluator result not provided"
            }
        
        return {
            "turns_to_consensus": turns,
            "stagnation": stagnation,
            "divergence": divergence,
            "consensus_detection": consensus_info,
            "efficiency_rating": self._calculate_efficiency_rating(turns, stagnation, divergence)
        }
    
    def _calculate_efficiency_rating(self, 
                                     turns: int, 
                                     stagnation: Dict, 
                                     divergence: Dict) -> str:
        """
        効率性の総合評価を計算
        
        Returns:
            str: "high", "medium", or "low"
        """
        # スコアリング
        score = 0
        
        # ターン数による評価 (少ないほど良い)
        if turns < 15:
            score += 2
        elif turns < 25:
            score += 1
        
        # 停滞率による評価 (低いほど良い)
        stagnation_rate = stagnation.get("stagnation_rate", 0)
        if stagnation_rate < 0.1:
            score += 2
        elif stagnation_rate < 0.2:
            score += 1
        
        # 発散率による評価 (低いほど良い)
        divergence_rate = divergence.get("divergence_rate", 0)
        if divergence_rate < 0.1:
            score += 2
        elif divergence_rate < 0.2:
            score += 1
        
        # 総合評価
        if score >= 5:
            return "high"
        elif score >= 3:
            return "medium"
        else:
            return "low"

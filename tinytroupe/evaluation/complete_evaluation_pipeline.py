# ========== evaluation_pipeline.py ==========
"""
評価パイプラインモジュール

シミュレーションの完全な評価を実行する統合パイプライン。
- ミクロ評価: MicroEvaluator (LLM-as-a-judge)
- マクロ評価: MacroEvaluator (ハイブリッド)
- プロセス指標: ProcessMetrics (LLM不使用)
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

from tinytroupe.environment import TinyWorld
from tinytroupe.agent import TinyPerson

from .deliverables import REQUIRED_DELIVERABLES
from .micro_evaluation import MicroEvaluator
from .macro_evaluation import MacroEvaluator
from .process_metrics import ProcessMetrics

logger = logging.getLogger("tinytroupe.evaluation")


class MeetingEvaluator:
    """
    会議シミュレーションの完全な評価パイプライン
    
    evaluation.md に基づく評価を実行:
    - RQ1 (ミクロ): Human feedback はエージェント行動の品質を向上させるか？
    - RQ2 (マクロ): 自律と参加型でシミュレーション結果はどう異なるか？
    """
    
    def __init__(self, 
                 model: str = "gpt-4o",
                 sample_size_per_agent: int = 5):
        """
        Args:
            model: 評価に使用するLLMモデル
            sample_size_per_agent: 各エージェントから評価するアクション数
        """
        self.micro_evaluator = MicroEvaluator(model=model)
        self.macro_evaluator = MacroEvaluator(model=model)
        self.process_metrics = ProcessMetrics()
        
        self.model = model
        self.sample_size_per_agent = sample_size_per_agent
    
    def evaluate_simulation(self, 
                           world: TinyWorld,
                           agents: List[TinyPerson],
                           meeting_topic: str,
                           condition_name: str = "unknown") -> Dict[str, Any]:
        """
        シミュレーション全体を評価
        
        Args:
            world: 会議ワールド
            agents: 参加エージェントのリスト
            meeting_topic: 会議の議題
            condition_name: 実験条件名 ("autonomous" or "participatory")
        
        Returns:
            dict: 評価結果の完全なレポート
        """
        print(f"\n{'='*70}")
        print(f"🔍 評価開始: {condition_name}")
        print(f"{'='*70}\n")
        
        # ========== 1. ミクロ評価 ==========
        print("📊 ミクロ評価（エージェント個別・LLM-as-a-judge）...")
        
        micro_results = self.micro_evaluator.evaluate_multiple_agents(
            agents=agents,
            meeting_topic=meeting_topic,
            sample_size_per_agent=self.sample_size_per_agent
        )
        
        print(f"  ✅ {len(agents)}名のエージェント評価完了")
        print(f"  📈 平均スコア: {micro_results['overall_average']}")
        
        # ========== 2. マクロ評価 ==========
        print("\n🌍 マクロ評価（シミュレーション全体）...")
        
        macro_results = self.macro_evaluator.evaluate_full(world)
        
        print(f"  ✅ 成果物抽出・評価完了")
        print(f"  📈 合意形成: {'成功' if macro_results['consensus']['success'] else '失敗'}")
        print(f"  📈 成果物品質: {macro_results['deliverables_quality'].get('overall_quality', 'N/A')}")
        
        # ========== 3. プロセス指標 ==========
        print("\n⏱️ プロセス指標（定量計算）...")
        
        # MacroEvaluatorの合意形成判定結果をProcessMetricsに渡す（統一した判定基準を使用）
        process_results = self.process_metrics.calculate_all_metrics(
            world=world,
            meeting_topic=meeting_topic,
            macro_consensus_result=macro_results["consensus"]  # MacroEvaluatorの結果を使用
        )
        
        print(f"  ✅ プロセス指標計算完了")
        print(f"  📈 ターン数: {process_results['turns_to_consensus']}")
        print(f"  📈 効率性: {process_results['efficiency_rating']}")
        
        # 合意形成達成状況の表示（MacroEvaluatorの判定に基づく）
        consensus_detection = process_results.get('consensus_detection', {})
        if consensus_detection.get('consensus_achieved'):
            total_turns = consensus_detection.get('total_turns', 0)
            print(f"  📈 合意形成達成: {total_turns}ターンで合意形成 (MacroEvaluator判定)")
        else:
            weak_areas = consensus_detection.get('weak_areas', [])
            if weak_areas:
                print(f"  ⚠️ 合意形成未達成 (弱点領域: {', '.join(weak_areas)})")
            else:
                print(f"  ⚠️ 合意形成未達成")
        
        # ========== 4. 介入統計（参加型条件のみ） ==========
        intervention_stats = None
        if condition_name == "participatory":
            print("\n📋 介入統計...")
            for agent in agents:
                if hasattr(agent, 'get_intervention_statistics'):
                    stats = agent.get_intervention_statistics()
                    if stats.get("total", 0) > 0:
                        intervention_stats = stats
                        print(f"  ✅ {agent.name}: 総介入 {stats['total']}回")
                        print(f"     - ACCEPT: {stats['by_type'].get('ACCEPT', 0)}")
                        print(f"     - GUIDE: {stats['by_type'].get('GUIDE', 0)}")
                        print(f"     - ガイドライン数: {stats['guidelines_count']}")
                        break
        
        # ========== 結果をまとめる ==========
        evaluation_report = {
            "metadata": {
                "condition": condition_name,
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "sample_size_per_agent": self.sample_size_per_agent
            },
            "meeting_topic": meeting_topic,
            
            # ミクロ評価 (RQ1)
            "micro_evaluation": {
                "agents": micro_results["agents"],
                "overall_average": micro_results["overall_average"],
                "overall_std": micro_results["overall_std"],
                "total_agents": micro_results["total_agents"]
            },
            
            # マクロ評価 (RQ2)
            "macro_evaluation": {
                "consensus": macro_results["consensus"],
                "deliverables": macro_results["deliverables"],
                "deliverables_quality": macro_results["deliverables_quality"],
                "contradictions": macro_results["contradictions"]
            },
            
            # プロセス指標 (RQ2)
            "process_metrics": process_results,
            
            # 介入統計（参加型条件のみ）
            "intervention_stats": intervention_stats,
            
            # 発話ログ（後から見返すため）
            "interaction_log": self._extract_interaction_log(world),
            
            # サマリー
            "summary": self._create_summary(micro_results, macro_results, process_results)
        }
        
        print(f"\n{'='*70}")
        print(f"✅ 評価完了: {condition_name}")
        print(f"{'='*70}")
        
        return evaluation_report
    
    def _extract_interaction_log(self, world: TinyWorld) -> List[Dict[str, Any]]:
        """
        発話ログを抽出（後から見返すため）
        
        Args:
            world: 会議ワールド
        
        Returns:
            List[Dict]: 発話ログのリスト
        """
        interaction_log = []
        
        for i, comm in enumerate(world._displayed_communications_buffer):
            if comm.get("action"):
                action = comm["action"]
                log_entry = {
                    "turn": i + 1,
                    "agent": comm.get("source", "Unknown"),
                    "type": action.get("type", "Unknown"),
                    "content": action.get("content", ""),
                    "target": action.get("target", None)
                }
                interaction_log.append(log_entry)
        
        return interaction_log
    
    def _create_summary(self, 
                       micro: Dict, 
                       macro: Dict, 
                       process: Dict) -> Dict[str, Any]:
        """評価結果のサマリーを作成"""
        return {
            # ミクロ評価サマリー
            "persona_consistency": micro["overall_average"].get("persona_consistency", 0),
            "logical_consistency": micro["overall_average"].get("logical_consistency", 0),
            "task_adherence": micro["overall_average"].get("task_adherence", 0),
            
            # マクロ評価サマリー
            "consensus_success": macro["consensus"].get("success", False),
            "overall_quality": macro["deliverables_quality"].get("overall_quality", 0),
            "contradiction_count": macro["contradictions"].get("total_count", 0),
            
            # プロセス指標サマリー
            "turns_to_consensus": process["turns_to_consensus"],
            "stagnation_rate": process["stagnation"].get("stagnation_rate", 0),
            "divergence_count": process["divergence"].get("divergence_count", 0),
            "efficiency_rating": process["efficiency_rating"]
        }
    
    def save_evaluation_report(self, 
                               report: Dict[str, Any], 
                               output_dir: str = "./evaluation_results") -> str:
        """
        評価レポートを保存
        
        Args:
            report: 評価レポート
            output_dir: 出力ディレクトリ
        
        Returns:
            str: 保存したファイルパス
        """
        os.makedirs(output_dir, exist_ok=True)
        
        condition = report["metadata"]["condition"]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{condition}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 評価レポートを保存しました: {filepath}")
        return filepath
    
    def compare_conditions(self, 
                          autonomous_report: Dict[str, Any],
                          participatory_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        自律条件と参加型条件を比較
        
        Args:
            autonomous_report: 自律条件の評価レポート
            participatory_report: 参加型条件の評価レポート
        
        Returns:
            dict: 比較結果
        """
        auto_summary = autonomous_report["summary"]
        part_summary = participatory_report["summary"]
        
        def calc_improvement(auto_val, part_val, higher_is_better=True):
            """改善率を計算"""
            if auto_val == 0:
                return None
            diff = part_val - auto_val
            rate = (diff / auto_val) * 100
            return rate if higher_is_better else -rate
        
        comparison = {
            "conditions": {
                "autonomous": auto_summary,
                "participatory": part_summary
            },
            
            "improvements": {
                # ミクロ評価 (高いほど良い)
                "persona_consistency": calc_improvement(
                    auto_summary["persona_consistency"],
                    part_summary["persona_consistency"],
                    higher_is_better=True
                ),
                "logical_consistency": calc_improvement(
                    auto_summary["logical_consistency"],
                    part_summary["logical_consistency"],
                    higher_is_better=True
                ),
                "task_adherence": calc_improvement(
                    auto_summary["task_adherence"],
                    part_summary["task_adherence"],
                    higher_is_better=True
                ),
                
                # マクロ評価 (品質は高いほど良い、矛盾は低いほど良い)
                "overall_quality": calc_improvement(
                    auto_summary["overall_quality"],
                    part_summary["overall_quality"],
                    higher_is_better=True
                ),
                "contradiction_reduction": calc_improvement(
                    auto_summary["contradiction_count"],
                    part_summary["contradiction_count"],
                    higher_is_better=False
                ),
                
                # プロセス指標 (ターン数・停滞・発散は低いほど良い)
                "efficiency_improvement": calc_improvement(
                    auto_summary["turns_to_consensus"],
                    part_summary["turns_to_consensus"],
                    higher_is_better=False
                ),
                "stagnation_reduction": calc_improvement(
                    auto_summary["stagnation_rate"],
                    part_summary["stagnation_rate"],
                    higher_is_better=False
                ),
                "divergence_reduction": calc_improvement(
                    auto_summary["divergence_count"],
                    part_summary["divergence_count"],
                    higher_is_better=False
                )
            },
            
            "success_comparison": {
                "autonomous_success": auto_summary["consensus_success"],
                "participatory_success": part_summary["consensus_success"]
            }
        }
        
        return comparison
    
    def print_comparison_summary(self, comparison: Dict[str, Any]):
        """比較結果のサマリーを表示"""
        print("\n" + "="*70)
        print("📊 条件比較サマリー")
        print("="*70)
        
        improvements = comparison["improvements"]
        
        print("\n🔬 ミクロ評価 (エージェント行動品質)")
        print(f"  Persona Consistency: {improvements['persona_consistency']:+.1f}%" if improvements['persona_consistency'] else "  Persona Consistency: N/A")
        print(f"  Logical Consistency: {improvements['logical_consistency']:+.1f}%" if improvements['logical_consistency'] else "  Logical Consistency: N/A")
        print(f"  Task Adherence: {improvements['task_adherence']:+.1f}%" if improvements['task_adherence'] else "  Task Adherence: N/A")
        
        print("\n🌍 マクロ評価 (成果品質)")
        print(f"  Overall Quality: {improvements['overall_quality']:+.1f}%" if improvements['overall_quality'] else "  Overall Quality: N/A")
        print(f"  Contradiction Reduction: {improvements['contradiction_reduction']:+.1f}%" if improvements['contradiction_reduction'] else "  Contradiction Reduction: N/A")
        
        print("\n⏱️ プロセス指標 (効率性)")
        print(f"  Efficiency (Turns): {improvements['efficiency_improvement']:+.1f}%" if improvements['efficiency_improvement'] else "  Efficiency: N/A")
        print(f"  Stagnation Reduction: {improvements['stagnation_reduction']:+.1f}%" if improvements['stagnation_reduction'] else "  Stagnation Reduction: N/A")
        print(f"  Divergence Reduction: {improvements['divergence_reduction']:+.1f}%" if improvements['divergence_reduction'] else "  Divergence Reduction: N/A")
        
        print("\n" + "="*70)


# 後方互換性のためのエイリアス
CompleteMeetingEvaluator = MeetingEvaluator

import json
from typing import Tuple, Dict, Any
from tinytroupe.agent import TinyPerson, logger
from tinytroupe.utils import JsonSerializableRegistry

class HumanCorrector(JsonSerializableRegistry):
    """
    人間がエージェントの出力を訂正するためのインターフェース
    
    エージェントが生成した暫定的な行動を人間に提示し、
    訂正・承認・却下のフィードバックを受け取る
    """
    
    serializable_attributes = ["agent_name", "correction_history"]
    
    def __init__(self, agent: TinyPerson):
        """
        Args:
            agent (TinyPerson): 訂正対象のエージェント
        """
        self.agent = agent
        self.agent_name = agent.name  # シリアライズ用
        self.correction_history = []  # 訂正履歴
        
    def present_for_correction(self, tentative_action: dict) -> Tuple[dict, Dict[str, Any]]:
        """
        エージェントの暫定行動を人間に提示して訂正を受け付ける
        
        Args:
            tentative_action (dict): エージェントが生成した暫定行動
                形式: {"type": "TALK", "content": "...", "target": "..."}
        
        Returns:
            Tuple[dict, Dict[str, Any]]: 
                - 訂正された行動 (None=再生成が必要)
                - 訂正フィードバック辞書
        """
        print(f"\n{'='*70}")
        print(f"🤖 [{self.agent.name}] が以下の行動を生成しました:")
        print(f"{'='*70}")
        print(f"タイプ: {tentative_action.get('type')}")
        print(f"内容: {tentative_action.get('content')}")
        print(f"ターゲット: {tentative_action.get('target', '')}")
        print(f"\n{'─'*70}")
        print("✏️  この行動を訂正しますか？")
        print(f"{'─'*70}")
        print("オプション:")
        print("  1. ACCEPT  - そのまま受け入れる")
        print("  2. MODIFY  - 内容を修正する")
        print("  3. REJECT  - 却下して新しい行動を指定")
        print("  4. EXPLAIN - 問題点を説明して再生成を促す")
        print(f"{'='*70}\n")
        
        choice = input("選択 (ACCEPT/MODIFY/REJECT/EXPLAIN): ").strip().upper()
        
        if choice == "ACCEPT":
            return tentative_action, self._create_acceptance_feedback()
        
        elif choice == "MODIFY":
            return self._modify_action(tentative_action)
        
        elif choice == "REJECT":
            return self._reject_and_replace(tentative_action)
        
        elif choice == "EXPLAIN":
            return self._explain_and_retry(tentative_action)
        
        else:
            print("⚠️  無効な選択です。ACCEPTとして処理します。")
            return tentative_action, self._create_acceptance_feedback()
    
    def _create_acceptance_feedback(self) -> Dict[str, Any]:
        """承認フィードバック"""
        return {
            "correction_type": "ACCEPT",
            "human_judgment": "The action was appropriate."
        }
    
    def _modify_action(self, original_action: dict) -> Tuple[dict, Dict[str, Any]]:
        """内容を修正"""
        print("\n📝 修正モード")
        print(f"現在の内容: {original_action.get('content')}")
        
        new_content = input("新しい内容: ").strip()
        
        corrected_action = original_action.copy()
        corrected_action["content"] = new_content
        
        feedback = {
            "correction_type": "MODIFY",
            "original_content": original_action.get("content"),
            "corrected_content": new_content,
            "human_judgment": f"Content modified to: {new_content}"
        }
        
        self._record_correction(feedback)
        return corrected_action, feedback
    
    def _reject_and_replace(self, original_action: dict) -> Tuple[dict, Dict[str, Any]]:
        """行動を却下して置き換え"""
        print("\n🚫 却下モード")
        
        new_type = input("新しいタイプ (TALK/THINK/DONE): ").strip().upper()
        new_content = input("内容: ").strip()
        new_target = input("ターゲット (なければEnter): ").strip()
        
        corrected_action = {
            "type": new_type,
            "content": new_content,
            "target": new_target if new_target else ""
        }
        
        feedback = {
            "correction_type": "REJECT",
            "original_action": original_action,
            "corrected_action": corrected_action,
            "human_judgment": f"Action replaced: {original_action.get('type')} -> {new_type}"
        }
        
        self._record_correction(feedback)
        return corrected_action, feedback
    
    def _explain_and_retry(self, original_action: dict) -> Tuple[None, Dict[str, Any]]:
        """説明を提供して再生成"""
        print("\n💡 説明モード")
        
        explanation = input("問題点: ").strip()
        suggestion = input("改善案: ").strip()
        
        feedback = {
            "correction_type": "EXPLAIN",
            "original_action": original_action,
            "human_judgment": f"Problem: {explanation}. Suggestion: {suggestion}"
        }
        
        self._record_correction(feedback)
        
        # Noneを返して再生成を促す
        return None, feedback
    
    def _record_correction(self, feedback: Dict[str, Any]):
        """訂正履歴を記録"""
        self.correction_history.append({
            "timestamp": self.agent.iso_datetime(),
            "agent_name": self.agent.name,
            "feedback": feedback
        })
        
        logger.info(f"[{self.agent.name}] Human correction: {feedback['correction_type']}")
    
    def get_correction_statistics(self) -> Dict[str, Any]:
        """訂正統計を取得"""
        total = len(self.correction_history)
        if total == 0:
            return {"total_corrections": 0}
        
        by_type = {}
        for correction in self.correction_history:
            correction_type = correction["feedback"]["correction_type"]
            by_type[correction_type] = by_type.get(correction_type, 0) + 1
        
        return {
            "total_corrections": total,
            "by_type": by_type,
            "acceptance_rate": by_type.get("ACCEPT", 0) / total if total > 0 else 0
        }
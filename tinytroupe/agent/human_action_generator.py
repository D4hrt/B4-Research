import json
import sys
import re
from tinytroupe.agent import logger
from tinytroupe.utils import JsonSerializableRegistry

class HumanActionGenerator(JsonSerializableRegistry):
    """
    人間の入力を受け取って、TinyPersonと同じフォーマットの行動を生成する
    LLM API呼び出しの代わりに、標準入力（input()）を使用する
    """
    
    def __init__(self, name: str = "Human"):
        """
        Args:
            name (str): 人間操作エージェントの名前
        """
        self.name = name
        self.total_actions_produced = 0
        
        # 統計情報（ActionGeneratorとの互換性のため）
        self.regeneration_attempts = 0
        self.direct_correction_attempts = 0
        self.regeneration_failures = 0
        self.direct_correction_failures = 0
        
    def generate_next_action(self, agent, current_messages: list):
        """
        人間からの入力を待ち、行動を生成する
        
        この関数はActionGenerator.generate_next_action()と同じインターフェースを実装し、
        LLM呼び出しの代わりに人間からの入力を取得する
        
        Args:
            agent: HumanControlledPersonインスタンス
            current_messages: 現在の会話履歴（表示用）
            
        Returns:
            (action, role, content, feedbacks)のタプル
        """
        self.total_actions_produced += 1
        
        # 最近の会話履歴を表示
        self._display_recent_context(current_messages)
        
        # 利用可能なエージェントのリストを表示
        self._display_accessible_agents(agent)
        
        # 人間からの入力を取得
        print(f"\n{'='*60}")
        print(f"🎮 [{self.name}] あなたのターンです！")
        print(f"{'='*60}")
        print("利用可能なコマンド:")
        print('  TALK "相手の名前" <メッセージ>  - 特定の相手に話しかける')
        print('  TALK <メッセージ>                - 全員に話しかける')
        print('  THINK <内容>                     - 思考する')
        print('  DONE                             - ターン終了')
        print(f"\n💡 ヒント: 名前にスペースが含まれる場合は引用符で囲んでください")
        print(f'   例: TALK "Emily Carter" Hello!')
        print(f"{'='*60}\n")
        
        actions = []
        
        while True:
            try:
                user_input = input(f"[{self.name}] >>> ").strip()
            except EOFError:
                # Jupyter Notebookなどで入力が終了した場合
                print("\n⚠️  入力が終了しました。DONEを発行します。")
                user_input = "DONE"
            
            if not user_input:
                continue
            
            # DONEコマンド
            if user_input.upper() == "DONE":
                if not actions:
                    # 何も行動していない場合はDONEアクションを追加
                    actions.append({
                        "type": "DONE",
                        "content": "",
                        "target": ""
                    })
                break
            
            # TALKコマンド
            elif user_input.upper().startswith("TALK "):
                rest = user_input[5:].strip()
                
                # ========== ここから修正 ==========
                # 引用符で囲まれた名前を検出するパターン
                # パターン: TALK "Name with spaces" message または TALK 'Name with spaces' message
                quoted_pattern = r'^["\']([^"\']+)["\']\s+(.+)$'
                match = re.match(quoted_pattern, rest)
                
                if match:
                    # 引用符で囲まれた名前が見つかった → 特定の相手に送信
                    target_name = match.group(1)
                    message = match.group(2)
                    
                    # ターゲットが存在するか確認
                    if self._is_valid_target(agent, target_name):
                        actions.append({
                            "type": "TALK",
                            "content": message,
                            "target": target_name
                        })
                        print(f"  → {target_name}に: {message}")
                    else:
                        print(f"  ❌ エラー: '{target_name}'は存在しないか、アクセスできません")
                        print(f"  💡 利用可能なエージェント:")
                        for a in agent._accessible_agents:
                            print(f"     - {a.name}")
                
                else:
                    # 引用符なし → 全員に送信
                    actions.append({
                        "type": "TALK",
                        "content": rest,
                        "target": ""
                    })
                    print(f"  → 全員に: {rest}")
                # ========== ここまで修正 ==========
            
            # THINKコマンド
            elif user_input.upper().startswith("THINK "):
                thought = user_input[6:].strip()
                actions.append({
                    "type": "THINK",
                    "content": thought,
                    "target": ""
                })
                print(f"  → 思考: {thought}")
            
            else:
                print(f"  ❌ 無効なコマンドです。'TALK', 'THINK', 'DONE'のいずれかを使用してください")
        
        # 最後の行動を返す（TinyPersonとの互換性のため）
        if actions:
            last_action = actions[-1]
        else:
            last_action = {"type": "DONE", "content": "", "target": ""}
        
        # TinyPersonと同じフォーマットで返す
        cognitive_action = {
            "action": last_action,
            "cognitive_state": self._get_minimal_cognitive_state()
        }
        
        # すべての行動をエージェントのアクションバッファに追加
        for action in actions:
            agent._actions_buffer.append(action)
        
        return last_action, "assistant", cognitive_action, []
    
    def _display_accessible_agents(self, agent):
        """利用可能なエージェントを表示"""
        if hasattr(agent, '_accessible_agents') and agent._accessible_agents:
            print(f"\n{'─'*60}")
            print("👥 現在インタラクション可能なエージェント:")
            print(f"{'─'*60}")
            for other_agent in agent._accessible_agents:
                print(f"  - {other_agent.name}")
            print()
        else:
            print(f"\n⚠️  現在、インタラクション可能なエージェントはいません。\n")
    
    def _display_recent_context(self, messages: list, n: int = 5):
        """最近のメッセージを表示"""
        print(f"\n{'─'*60}")
        print("📜 最近の会話:")
        print(f"{'─'*60}")
        
        recent = messages[-n:] if len(messages) > n else messages
        
        if not recent:
            print("  (まだ会話はありません)")
        
        for msg in recent:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # contentが辞書の場合は整形
            if isinstance(content, dict):
                if "action" in content:
                    action = content["action"]
                    action_type = action.get("type", "")
                    action_content = action.get("content", "")
                    target = action.get("target", "")
                    
                    if target:
                        print(f"  [{role}] {action_type} → {target}: {action_content[:100]}")
                    else:
                        print(f"  [{role}] {action_type}: {action_content[:100]}")
                
                elif "stimuli" in content:
                    for stimulus in content["stimuli"]:
                        stim_type = stimulus.get("type", "")
                        stim_content = stimulus.get("content", "")
                        source = stimulus.get("source", "")
                        print(f"  [{role}] {stim_type} from {source}: {stim_content[:100]}")
            
            elif isinstance(content, str):
                try:
                    content_dict = json.loads(content)
                    if "action" in content_dict:
                        action = content_dict["action"]
                        print(f"  [{role}] {action.get('type')}: {action.get('content', '')[:100]}")
                except json.JSONDecodeError:
                    print(f"  [{role}] {str(content)[:100]}")
        
        print()
    
    def _is_valid_target(self, agent, target_name: str) -> bool:
        """ターゲットが有効かチェック"""
        if not hasattr(agent, '_accessible_agents'):
            return False
        
        return any(a.name == target_name for a in agent._accessible_agents)
    
    def _get_minimal_cognitive_state(self) -> dict:
        """最小限の認知状態を返す"""
        return {
            "goals": "Participate in the conversation as a human",
            "context": ["Human-controlled agent participating in simulation"],
            "attention": "Current conversation",
            "emotions": "Neutral (human-controlled)"
        }
    
    def get_statistics(self):
        """統計情報を返す（ActionGeneratorとの互換性）"""
        return {
            "total_actions_produced": self.total_actions_produced,
            "regeneration_attempts": 0,
            "direct_correction_attempts": 0,
            "regeneration_failures": 0,
            "direct_correction_failures": 0,
            "original_success_rate": 1.0
        }
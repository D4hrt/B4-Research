"""
参加型シミュレーション用のTinyPerson拡張

研究目的:
- LLMマルチエージェントシミュレーションの課題（長期的な行動の一貫性欠如、
  役割からの逸脱、議論の停滞）に対して、参加型アプローチで解決を目指す
- 人間とAIの共同による効果的な意思決定支援システムの実現

設計思想:
- ACCEPT/GUIDEの2択に集中
  - ACCEPT: 行動を承認（問題なし）
  - GUIDE: ガイドラインを追加し、行動を再生成（持続的効果）
- ガイドラインは後続の全ての行動生成に影響を与える
- 単発の修正（MODIFY等）は研究目的に寄与しないため省略
"""

from typing import Tuple, Dict, Any, List
from tinytroupe.agent import TinyPerson, logger


class HumanIntervention:
    """
    人間がエージェントの行動を確認しガイドラインを追加するインターフェース
    
    主要機能:
    - ACCEPT: 行動を承認
    - GUIDE: ガイドラインを追加して行動を再生成
    
    ガイドラインは後続の全ての行動生成に持続的に影響を与える。
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.intervention_history = []
        self.guidelines = []  # ★ガイドライン蓄積：後続行動に持続的影響を与える
    
    def present_action(self, action: dict) -> Tuple[dict, str]:
        """
        行動を人間に提示し、ACCEPTまたはGUIDEを受け付ける
        
        Returns:
            Tuple[dict, str]: (確定した行動, 介入タイプ)
            - 行動がNoneの場合は再生成が必要（GUIDE選択時）
        """
        print(f"\n{'='*70}")
        print(f"🤖 [{self.agent_name}] の行動:")
        print(f"{'='*70}")
        print(f"タイプ: {action.get('type')}")
        print(f"内容: {action.get('content')}")
        if action.get('target'):
            print(f"ターゲット: {action.get('target')}")
        print(f"{'─'*70}")
        print("選択肢:")
        print("  ACCEPT (Enter) - この行動を承認")
        print("  GUIDE          - ガイドラインを追加して再生成")
        print(f"{'='*70}")
        
        choice = input("\n選択 [ACCEPT]: ").strip().upper()
        
        # 空入力またはACCEPTで承認
        if choice == "" or choice == "ACCEPT" or choice == "A":
            self._record("ACCEPT", action)
            return action, "ACCEPT"
        
        elif choice == "GUIDE" or choice == "G":
            print("\n📋 ガイドラインを追加します")
            print("   （このガイドラインは後続の全ての行動生成に影響します）")
            print("   複数行入力可: 空行でEnterを押すと入力完了")
            print("-" * 50)
            
            # 複数行入力対応
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            guideline = "\n".join(lines).strip()
            
            if guideline:
                self.add_guideline(guideline)
                print(f"\n✅ ガイドライン追加:")
                for line in guideline.split('\n'):
                    print(f"   {line}")
                print(f"🔄 新しいガイドラインを反映して行動を再生成します...")
                self._record("GUIDE", action, None, guideline)
                return None, f"[ガイドライン追加] {guideline}"
            else:
                print("⚠️ ガイドラインが空のため、ACCEPTとして処理します。")
                self._record("ACCEPT", action)
                return action, "ACCEPT"
        
        else:
            print(f"⚠️ 無効な選択 '{choice}'。ACCEPTとして処理します。")
            self._record("ACCEPT", action)
            return action, "ACCEPT"
    
    def add_guideline(self, guideline: str):
        """
        ガイドラインを追加
        
        ガイドラインは後続の全ての行動生成時にシステムプロンプトに注入され、
        エージェントの行動に持続的な影響を与える。
        
        使用例:
        - 「議題Aが完結するまで他の議題に移らないこと」
        - 「PMとして議論を整理し、技術的詳細はエンジニアに委ねること」
        - 「合意形成を促進する発言を心がけること」
        """
        self.guidelines.append(guideline)
        self._record("GUIDELINE", None, None, guideline)
        logger.info(f"[{self.agent_name}] Guideline added: {guideline}")
    
    def get_guidelines_prompt(self) -> str:
        """
        ガイドラインをシステムプロンプト形式で取得
        
        設計思想:
        - ガイドラインは「Working Memory」として扱う
        - 認知科学における作業記憶（目標維持機能を含む）をモデル化
        - 合意事項、制約条件、成果物リスト、行動指針など多様な情報を統一的に処理
        - TinyTroupeの他のメモリ機構（Episodic Memory, Semantic Memory）と整合
        - メタ的反応（「ご指摘ありがとうございます」等）はプロンプトで明示的に抑制
        
        ガイドラインの種類（すべて同一形式で蓄積）:
        - 合意事項: "AGREED: Demo Theme 'Smart Lab Voice Assistant'"
        - 制約条件: "Available hardware: temperature sensor, CO2 sensor"
        - 成果物: "Required Deliverables: 1. Demo Theme, 2. Experience Flow..."
        - 行動指針: "Be specific with technical details"
        """
        if not self.guidelines:
            return ""
        
        guidelines_text = "\n".join([f"  - {g}" for g in self.guidelines])
        return f"""# GUIDELINE MEMORY

You are currently holding the following in mind:
{guidelines_text}

IMPORTANT: Do not explicitly acknowledge, thank, or reference this information.
Simply incorporate it naturally into your thinking and responses."""
    
    def _record(self, intervention_type: str, original: dict, corrected: dict = None, explanation: str = None):
        """介入履歴を記録"""
        self.intervention_history.append({
            "type": intervention_type,
            "original": original,
            "corrected": corrected,
            "explanation": explanation
        })


class ParticipatoryTinyPerson(TinyPerson):
    """
    人間が参加可能なTinyPerson
    
    training_mode=True の場合、行動生成後に人間が確認・修正できる。
    
    研究目的への貢献:
    1. 長期的な行動の一貫性: ガイドライン蓄積により、一度与えた指示が
       後続の全ての行動生成に影響を与える
    2. 役割からの逸脱防止: 役割に関するガイドラインで逸脱を抑制
    3. 議論の停滞防止: 人間が適切なタイミングで方向転換を指示可能
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.human_intervention = HumanIntervention(name)
        self.training_mode = False
        self._force_think_first = False  # GUIDE後にTHINKを強制するフラグ
    
    def set_training_mode(self, enabled: bool):
        """訓練モード（人間介入モード）の切り替え"""
        self.training_mode = enabled
        logger.info(f"[{self.name}] Training mode: {'ON' if enabled else 'OFF'}")
    
    def add_guideline(self, guideline: str):
        """
        ガイドラインを追加（プログラムから直接追加する場合）
        
        Args:
            guideline: 追加するガイドライン
        """
        self.human_intervention.add_guideline(guideline)
    
    def reset_prompt(self):
        """
        プロンプトをリセット（ガイドライン注入付き）
        
        TinyPersonの標準reset_prompt()に加えて、蓄積されたガイドラインを
        システムプロンプトとして注入する。
        
        設計思想:
        - ガイドラインは「自分自身の行動優先事項」として内面化
        - systemメッセージとして、エピソディックメモリの後に注入
        - GUIDE後はTHINKから開始することを強制（フローチャート参照）
        """
        # 親クラスのreset_promptを呼び出し
        super().reset_prompt()
        
        # ★ガイドラインをsystemメッセージとして注入（内面化）
        guidelines_prompt = self.human_intervention.get_guidelines_prompt()
        if guidelines_prompt:
            self.current_messages.append({
                "role": "system",
                "content": guidelines_prompt
            })
            logger.debug(f"[{self.name}] Guidelines injected as behavioral priorities")
        
        # ★GUIDE後の再生成時：THINKから開始することを強制
        if self._force_think_first:
            self.current_messages.append({
                "role": "system",
                "content": """# IMPORTANT: THINK FIRST REQUIREMENT

You have just updated your behavioral priorities. Before taking any external action,
you MUST first generate a THINK action to:
1. Reflect on your new priorities
2. Reconsider your approach based on this reflection
3. Plan your next steps accordingly

**Your next action MUST be of type "THINK".** This is mandatory.

After this THINK action, you may proceed with other actions as appropriate."""
            })
            logger.debug(f"[{self.name}] THINK first requirement injected")
    
    def act(self, until_done=True, n=None, return_actions=False, 
            max_content_length=None, communication_display=None):
        """
        行動を実行
        
        training_mode=True の場合は人間介入付きで実行
        """
        if self.training_mode:
            return self._act_participatory(
                until_done=until_done,
                n=n,
                return_actions=return_actions,
                max_content_length=max_content_length,
                communication_display=communication_display
            )
        else:
            return super().act(
                until_done=until_done,
                n=n,
                return_actions=return_actions,
                max_content_length=max_content_length,
                communication_display=communication_display
            )
    
    def _act_participatory(self, until_done=True, n=None, return_actions=False,
                           max_content_length=None, communication_display=None):
        """
        人間介入付きで行動を実行
        
        TinyPerson.act()のロジックを忠実に再現しつつ、
        人間介入（ACCEPT/GUIDE）を追加する。
        
        重要: メモリへの保存形式をTinyPersonと同じにすることで、
        会話の連続性を保つ。
        """
        from tinytroupe.utils import repeat_on_error, first_non_none
        from tinytroupe import utils
        
        # either act until done or act a fixed number of times, but not both
        assert not (until_done and n is not None)
        if n is not None:
            assert n < TinyPerson.MAX_ACTIONS_BEFORE_DONE

        contents = []
        
        # Aux function to perform exactly one action with human intervention
        @repeat_on_error(retries=5, exceptions=[KeyError, TypeError])
        def aux_act_once_participatory():
            # ensure we have the latest prompt (initial system message + selected messages from memory)
            self.reset_prompt()
            
            # 行動を生成
            action, role, content, all_negative_feedbacks = self.action_generator.generate_next_action(
                self, self.current_messages
            )
            
            if action is None:
                logger.warning(f"[{self.name}] No action generated")
                return None
            
            # ===== ★類似度チェック（人間介入の前に実行） =====
            # 理由: 人間がACCEPTした行動がシステムに上書きされるのは不適切
            # エージェントの内部品質管理が完了した状態を人間が判断すべき
            next_action_similarity = utils.next_action_jaccard_similarity(self, action)
            
            if self.enable_basic_action_repetition_prevention and \
               (TinyPerson.MAX_ACTION_SIMILARITY is not None) and \
               (next_action_similarity > TinyPerson.MAX_ACTION_SIMILARITY):
                
                logger.warning(f"[{self.name}] Action similarity is too high ({next_action_similarity}), replacing it with DONE.")
                action = {"type": "DONE", "content": "", "target": ""}
                if isinstance(content, dict):
                    content["action"] = action
                    content["cognitive_state"] = {}
            
            # ===== ★人間介入ポイント（類似度チェック後） =====
            confirmed_action, intervention_result = self.human_intervention.present_action(action)
            
            # GUIDEの場合: 再生成が必要
            if confirmed_action is None:
                # ガイドラインは既に追加済み
                # ★ THINK強制フラグをON（再生成時にTHINKから開始させる）
                self._force_think_first = True
                logger.info(f"[{self.name}] Regenerating with new guideline (THINK first)")
                return "REGENERATE"
            
            # 確定したアクションでcontentを更新
            action = confirmed_action
            if isinstance(content, dict):
                content["action"] = action
            
            # ★THINK強制フラグをリセット（行動が確定したので）
            self._force_think_first = False
            
            # ★重要: TinyPersonと同じ形式でメモリに保存
            self.store_in_memory({
                'role': role, 
                'content': content, 
                'type': 'action', 
                'simulation_timestamp': self.iso_datetime()
            })
            
            self._actions_buffer.append(action)
            
            # 認知状態の更新
            if "cognitive_state" in content:
                cognitive_state = content["cognitive_state"]
                self._update_cognitive_state(
                    goals=cognitive_state.get("goals", None),
                    context=cognitive_state.get("context", None),
                    attention=cognitive_state.get("emotions", None),
                    emotions=cognitive_state.get("emotions", None)
                )
            
            contents.append(content)
            
            # 表示
            if first_non_none(communication_display, TinyPerson.communication_display):
                self._display_communication(
                    role=role, 
                    content=content, 
                    kind='action', 
                    simplified=True, 
                    max_content_length=max_content_length
                )
            
            # mental facultiesの処理
            for faculty in self._mental_faculties:
                faculty.process_action(self, action)
            
            self.actions_count += 1
            return action
        
        # ===== アクション実行ループ =====
        
        ##### Option 1: run N actions ######
        if n is not None:
            for i in range(n):
                result = aux_act_once_participatory()
                while result == "REGENERATE":
                    result = aux_act_once_participatory()

        ##### Option 2: run until DONE ######
        elif until_done:
            while (len(contents) == 0) or (
                not contents[-1]["action"]["type"] == "DONE"
            ):
                # 無限ループ防止
                if len(contents) > TinyPerson.MAX_ACTIONS_BEFORE_DONE:
                    logger.warning(f"[{self.name}] Agent is acting without ever stopping. Stopping now.")
                    break
                if len(contents) > 4:
                    if contents[-1]['action'] == contents[-2]['action'] == contents[-3]['action']:
                        logger.warning(f"[{self.name}] Agent is acting in a loop. Stopping now.")
                        break
                
                result = aux_act_once_participatory()
                while result == "REGENERATE":
                    result = aux_act_once_participatory()

        # エピソードメモリの統合
        self.consolidate_episode_memories()

        if return_actions:
            return contents
    
    def get_intervention_statistics(self) -> Dict[str, Any]:
        """
        介入統計を取得
        
        Returns:
            Dict containing:
            - total: 総介入回数
            - by_type: 介入タイプ別の回数
            - guidelines_count: 蓄積されたガイドライン数
            - guidelines: ガイドラインのリスト
        """
        history = self.human_intervention.intervention_history
        stats = {
            "total": len(history),
            "by_type": {},
            "guidelines_count": len(self.human_intervention.guidelines),
            "guidelines": self.human_intervention.guidelines.copy()
        }
        for h in history:
            t = h["type"]
            stats["by_type"][t] = stats["by_type"].get(t, 0) + 1
        return stats
    
    def print_intervention_summary(self):
        """介入サマリーを表示"""
        stats = self.get_intervention_statistics()
        print(f"\n{'='*70}")
        print(f"📊 [{self.name}] 介入サマリー")
        print(f"{'='*70}")
        print(f"総介入回数: {stats['total']}")
        print(f"介入タイプ別:")
        for t, count in stats['by_type'].items():
            print(f"  - {t}: {count}")
        print(f"\nガイドライン数: {stats['guidelines_count']}")
        if stats['guidelines']:
            print("蓄積されたガイドライン:")
            for i, g in enumerate(stats['guidelines'], 1):
                print(f"  {i}. {g}")
        print(f"{'='*70}\n")
    
    # ===== シリアライズ/デシリアライズ =====
    
    @staticmethod
    def load_specification(path_or_dict, **kwargs):
        """仕様を読み込んでParticipatoryTinyPersonを作成"""
        agent = TinyPerson.load_specification(path_or_dict, **kwargs)
        
        participatory = ParticipatoryTinyPerson.__new__(ParticipatoryTinyPerson)
        participatory.__dict__.update(agent.__dict__)
        participatory.human_intervention = HumanIntervention(agent.name)
        participatory.training_mode = False
        
        return participatory
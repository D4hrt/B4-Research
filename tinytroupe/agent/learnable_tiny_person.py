import json
from tinytroupe.agent import TinyPerson, logger
from tinytroupe.agent.human_corrector import HumanCorrector

class LearnableTinyPerson(TinyPerson):
    """
    人間からの介入を受け付けるTinyPerson
    """
    
    def __init__(self, name: str, **kwargs):
        super().__init__(name=name, **kwargs)
        
        self.human_corrector = HumanCorrector(self)
        self.training_mode = False
        
        self.intervention_statistics = {
            "total_interventions": 0,
            "interventions_by_type": {},
            "actions_generated": 0,
            "actions_accepted_without_intervention": 0,
            "quality_check_failures": 0,
            "quality_check_passes": 0
        }
    
    def set_training_mode(self, enabled: bool):
        self.training_mode = enabled
        logger.info(f"[{self.name}] Training mode: {'enabled' if enabled else 'disabled'}")
    
    def act(self, until_done=True, n=None, return_actions=False, max_content_length=None, communication_display=None):
        if self.training_mode:
            return self.act_with_human_intervention(
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
    
    def act_with_human_intervention(self, 
                                    until_done=True, 
                                    n=None, 
                                    return_actions=False,
                                    max_content_length=None,
                                    communication_display:bool=None):
        """
        人間の介入を受け付けながら行動
        """
        actions_taken = []
        action_count = 0
        
        while True:
            if n is not None and action_count >= n:
                logger.debug(f"[{self.name}] Reached maximum action count ({n})")
                break
            
            # ========== デバッグ: reset_prompt() 前の状態 ==========
            print(f"\n{'='*70}")
            print(f"[DEBUG] [{self.name}] BEFORE reset_prompt() - Action #{action_count + 1}")
            print(f"{'='*70}")
            print(f"Episodic memory count: {len(self.episodic_memory.retrieve_all())}")
            print(f"Last 3 episodic memories:")
            for i, mem in enumerate(self.episodic_memory.retrieve_all()[-3:]):
                print(f"  [{i}] type={mem.get('type')}, content[:150]={str(mem.get('content'))[:150]}")
            print(f"{'='*70}\n")
            
            # ========== プロンプトリセット ==========
            logger.info(f"[{self.name}] Resetting prompt to include latest episodic memories...")
            self.reset_prompt()
            
            # ========== デバッグ: reset_prompt() 後の状態 ==========
            print(f"\n{'='*70}")
            print(f"[DEBUG] [{self.name}] AFTER reset_prompt()")
            print(f"{'='*70}")
            print(f"Current messages count: {len(self.current_messages)}")
            print(f"Last 3 messages in current_messages:")
            for i, msg in enumerate(self.current_messages[-3:]):
                print(f"  [{i}] role={msg.get('role')}")
                if isinstance(msg.get('content'), str):
                    print(f"      content[:200]={msg.get('content')[:200]}")
                elif isinstance(msg.get('content'), dict):
                    print(f"      content_keys={msg.get('content').keys()}")
            print(f"{'='*70}\n")
            
            # ========== 修正: role=None のメッセージを修正 ==========
            for msg in self.current_messages:
                if isinstance(msg, dict) and msg.get("role") is None:
                    # roleが設定されていない場合、contentから推定
                    content = msg.get("content")
                    
                    # contentが辞書の場合
                    if isinstance(content, dict):
                        if "action" in content:
                            msg["role"] = "assistant"
                        elif "stimuli" in content:
                            msg["role"] = "user"
                        else:
                            msg["role"] = "system"
                    
                    # contentが文字列の場合
                    elif isinstance(content, str):
                        # action系のメモリはassistant
                        msg["role"] = "assistant"
            # ========== ここまで修正 ==========
            
            # ========== 修正: try ブロックを追加 ==========
            try:
                # current_messages のクリーンアップ
                cleaned_messages = []
                for msg in self.current_messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        cleaned_messages.append(msg)
                    else:
                        logger.warning(f"[{self.name}] Skipping invalid message: {msg}")
                
                logger.debug(f"[{self.name}] Cleaned {len(self.current_messages)} messages to {len(cleaned_messages)} valid messages")
                
                # ActionGeneratorに最新のメッセージを渡す
                tentative_action, role, content, feedbacks = \
                    self.action_generator.generate_next_action(
                        self, 
                        cleaned_messages
                    )
                
                # 品質チェックの結果を記録
                if len(feedbacks) > 0:
                    self.intervention_statistics["quality_check_failures"] += len(feedbacks)
                    logger.info(f"[{self.name}] ActionGenerator performed {len(feedbacks)} quality corrections")
                else:
                    self.intervention_statistics["quality_check_passes"] += 1
                
                logger.info(f"[{self.name}] ✅ High-quality action generated successfully!")
                logger.info(f"[{self.name}] Generated action type: {tentative_action.get('type')}")
                logger.info(f"[{self.name}] Generated action content: {tentative_action.get('content', '')[:100]}")
                
            except Exception as e:
                logger.error(f"[{self.name}] ❌ EXCEPTION in generate_next_action()!")
                logger.error(f"[{self.name}] Exception type: {type(e).__name__}")
                logger.error(f"[{self.name}] Exception message: {str(e)}")
                logger.error(f"[{self.name}] Traceback:", exc_info=True)
                
                tentative_action = {"type": "DONE", "content": "", "target": ""}
                role = "assistant"
                content = {
                    "action": tentative_action,
                    "cognitive_state": {
                        "goals": self._mental_state.get("goals", ""),
                        "context": self._mental_state.get("context", []),
                        "attention": self._mental_state.get("attention", ""),
                        "emotions": self._mental_state.get("emotions", "")
                    }
                }
                feedbacks = []
                
                logger.warning(f"[{self.name}] Fallback to DONE action due to exception")
            # ========== ここまで修正 ==========
            
            self.intervention_statistics["actions_generated"] += 1
            
            # ========== 品質チェック済みの行動を人間に提示 ==========
            corrected_action, intervention_feedback = \
                self.human_corrector.present_for_correction(tentative_action)
            
            logger.info(f"[{self.name}] Human intervention completed")
            logger.info(f"[{self.name}] Intervention type: {intervention_feedback.get('correction_type')}")
            
            # Noneの場合は再生成が必要
            if corrected_action is None:
                logger.debug(f"[{self.name}] Action was rejected, requesting regeneration")
                
                # ========== デバッグ: フィードバック保存前 ==========
                print(f"\n{'='*70}")
                print(f"[DEBUG] [{self.name}] BEFORE saving feedback")
                print(f"{'='*70}")
                print(f"Feedback to save:")
                print(f"  human_judgment: {intervention_feedback.get('human_judgment', '')[:200]}")
                print(f"{'='*70}\n")
                
                # フィードバックを stimulus として保存
                feedback_stimulus = {
                    "type": "CONVERSATION",
                    "content": intervention_feedback.get("human_judgment", ""),
                    "source": "human_corrector"
                }
                
                # _observe() を使って保存
                self._observe(
                    stimulus=[feedback_stimulus],
                    max_content_length=max_content_length,
                    communication_display=communication_display
                )
                
                # ========== デバッグ: フィードバック保存後 ==========
                print(f"\n{'='*70}")
                print(f"[DEBUG] [{self.name}] AFTER saving feedback")
                print(f"{'='*70}")
                print(f"Episodic memory count: {len(self.episodic_memory.retrieve_all())}")
                print(f"Last episodic memory:")
                last_mem = self.episodic_memory.retrieve_all()[-1] if len(self.episodic_memory.retrieve_all()) > 0 else None
                if last_mem:
                    print(f"  type={last_mem.get('type')}, content[:200]={str(last_mem.get('content'))[:200]}")
                print(f"{'='*70}\n")
                
                logger.debug(f"[{self.name}] Added feedback to memory using _observe()")
                continue
            
            # 介入統計を更新
            if intervention_feedback["correction_type"] != "ACCEPT":
                self.intervention_statistics["total_interventions"] += 1
                
                correction_type = intervention_feedback["correction_type"]
                self.intervention_statistics["interventions_by_type"][correction_type] = \
                    self.intervention_statistics["interventions_by_type"].get(correction_type, 0) + 1
            else:
                self.intervention_statistics["actions_accepted_without_intervention"] += 1

            # contentの'action'キーを更新
            if isinstance(content, dict):
                content["action"] = corrected_action
            else:
                content = {
                    "action": corrected_action,
                    "cognitive_state": {
                        "goals": self._mental_state.get("goals", ""),
                        "context": self._mental_state.get("context", []),
                        "attention": self._mental_state.get("attention", ""),
                        "emotions": self._mental_state.get("emotions", "")
                    }
                }
        
            # 修正後の内容を表示
            self._display_communication(
                role=role,
                content=content,
                kind="action",
                simplified=True,
                max_content_length=max_content_length
            )
            
            # ========== デバッグ: 行動保存前 ==========
            print(f"\n{'='*70}")
            print(f"[DEBUG] [{self.name}] BEFORE saving corrected action")
            print(f"{'='*70}")
            print(f"Corrected action:")
            print(f"  type={corrected_action['type']}, content[:200]={corrected_action['content'][:200]}")
            print(f"{'='*70}\n")
            
            # メモリに保存
            self.store_in_memory({
                "type": "action",
                "content": corrected_action["content"],
                "action_type": corrected_action["type"],
                "target": corrected_action.get("target", ""),
                "simulation_timestamp": self.iso_datetime()
            })
            
            # ========== デバッグ: 行動保存後 ==========
            print(f"\n{'='*70}")
            print(f"[DEBUG] [{self.name}] AFTER saving corrected action")
            print(f"{'='*70}")
            print(f"Episodic memory count: {len(self.episodic_memory.retrieve_all())}")
            print(f"Last episodic memory:")
            last_mem = self.episodic_memory.retrieve_all()[-1]
            print(f"  type={last_mem.get('type')}, content[:200]={str(last_mem.get('content'))[:200]}")
            print(f"{'='*70}\n")
            
            # 訂正された行動を実行
            self._actions_buffer.append(corrected_action)
            actions_taken.append(corrected_action)
            
            # メッセージ履歴に追加
            self.current_messages.append({
                "role": role,
                "content": content
            })
            
            # 行動数をインクリメント
            action_count += 1
            
            logger.info(f"[{self.name}] Action #{action_count} completed successfully")
            
            # DONEの場合は終了
            if corrected_action["type"] == "DONE":
                logger.debug(f"[{self.name}] DONE action confirmed, ending turn")
                break
            
            # until_done=Falseかつn回に達した場合も終了
            if not until_done and n is not None and action_count >= n:
                logger.debug(f"[{self.name}] Reached n={n} actions without DONE")
                break
    
        logger.info(f"[{self.name}] ========== act_with_human_intervention() END ==========")
        logger.info(f"[{self.name}] Total actions taken: {action_count}")
    
        if return_actions:
            return actions_taken
    
    def get_intervention_statistics(self) -> dict:
        """介入統計を取得"""
        stats = self.intervention_statistics.copy()
        
        total = stats["actions_generated"]
        if total > 0:
            stats["acceptance_rate"] = \
                stats["actions_accepted_without_intervention"] / total
            stats["intervention_rate"] = \
                stats["total_interventions"] / total
            
            total_quality_checks = stats["quality_check_passes"] + stats["quality_check_failures"]
            if total_quality_checks > 0:
                stats["quality_check_pass_rate"] = \
                    stats["quality_check_passes"] / total_quality_checks
        
        return stats
    
    def save_specification(self, path: str):
        """仕様を保存"""
        super().save_specification(
            path,
            include_mental_faculties=True,
            include_memory=True,
            include_mental_state=True
        )
        
        logger.info(f"[{self.name}] Saved specification to {path}")
    
    @staticmethod
    def load_specification(path_or_dict, **kwargs):
        """エージェントを読み込む"""
        agent = TinyPerson.load_specification(path_or_dict, **kwargs)
        
        learnable = LearnableTinyPerson.__new__(LearnableTinyPerson)
        learnable.__dict__.update(agent.__dict__)
        
        learnable.human_corrector = HumanCorrector(learnable)
        
        if not hasattr(learnable, 'training_mode'):
            learnable.training_mode = False
        
        if not hasattr(learnable, 'intervention_statistics'):
            learnable.intervention_statistics = {
                "total_interventions": 0,
                "interventions_by_type": {},
                "actions_generated": 0,
                "actions_accepted_without_intervention": 0,
                "quality_check_failures": 0,
                "quality_check_passes": 0
            }
        
        return learnable
from tinytroupe.agent import TinyPerson
from tinytroupe.agent.human_action_generator import HumanActionGenerator
from tinytroupe.agent.memory import EpisodicMemory, SemanticMemory
import json

class HumanControlledPerson(TinyPerson):
    """
    人間が操作するエージェント
    
    TinyPersonを継承し、ActionGeneratorをHumanActionGeneratorに置き換えることで、
    LLM呼び出しの代わりに人間からの入力を使用する
    """
    
    def __init__(self, name: str, persona: dict = None):
        """
        Args:
            name (str): エージェントの名前
            persona (dict, optional): ペルソナ定義（推奨）
                他のエージェントがこの人間操作エージェントを認識するために必要
        """
        # HumanActionGeneratorを使用
        super().__init__(
            name=name,
            action_generator=HumanActionGenerator(name=name),
            episodic_memory=EpisodicMemory(),
            semantic_memory=None,  # セマンティックメモリは不要
            enable_basic_action_repetition_prevention=False  # 人間には不要
        )
        
        # ペルソナを設定
        if persona:
            self._persona.update(persona)
        else:
            # デフォルトで人間操作であることを示す最小限のペルソナ
            self._persona.update({
                "name": name,
                "age": None,
                "nationality": "Human Participant",
                "occupation": "Simulation Participant",
                "routine": "Participating in this simulation",
                "personality_traits": {
                    "openness": None,
                    "conscientiousness": None,
                    "extraversion": None,
                    "agreeableness": None,
                    "neuroticism": None
                }
            })
        
        self.reset_prompt()
    
    def minibio(self, extended=False, requirements=None):
        """人間操作エージェントの簡易プロフィール"""
        if extended:
            return f"{self.name} is a human participant in this simulation."
        else:
            return f"{self.name} (human participant)"
    
    @staticmethod
    def load_specification(path_or_dict, 
                          suppress_mental_faculties=False, 
                          suppress_memory=False, 
                          suppress_mental_state=False, 
                          auto_rename_agent=False, 
                          new_agent_name=None):
        """
        JSONファイルまたは辞書から人間操作エージェントを読み込む
        
        Args:
            path_or_dict (str or dict): JSONファイルのパスまたはペルソナ辞書
            suppress_mental_faculties (bool, optional): メンタルファカルティを抑制するか
            suppress_memory (bool, optional): メモリを抑制するか
            suppress_mental_state (bool, optional): メンタルステートを抑制するか
            auto_rename_agent (bool, optional): 自動リネームするか
            new_agent_name (str, optional): 新しいエージェント名
        
        Returns:
            HumanControlledPerson: 読み込まれた人間操作エージェント
        """
        # JSONファイルまたは辞書を読み込む
        if isinstance(path_or_dict, str):
            with open(path_or_dict, 'r', encoding='utf-8') as f:
                spec = json.load(f)
        elif isinstance(path_or_dict, dict):
            spec = path_or_dict
        else:
            raise ValueError("path_or_dict must be either a file path (str) or a dictionary")
        
        # ペルソナを抽出
        persona = spec.get("persona", {})
        
        # エージェント名を決定
        if new_agent_name:
            agent_name = new_agent_name
        elif auto_rename_agent:
            # 自動リネーム: 既存の名前に番号を追加
            base_name = persona.get("name", "HumanAgent")
            agent_name = base_name
            counter = 1
            while TinyPerson.has_agent(agent_name):
                agent_name = f"{base_name}_{counter}"
                counter += 1
        else:
            agent_name = persona.get("name", "HumanAgent")
        
        # HumanControlledPersonインスタンスを作成
        human_agent = HumanControlledPerson(name=agent_name, persona=persona)
        
        # メモリとメンタルステートを復元（必要な場合）
        if not suppress_memory:
            if "episodic_memory" in spec:
                from tinytroupe.agent.memory import EpisodicMemory
                human_agent.episodic_memory = EpisodicMemory.from_json(spec["episodic_memory"])
            
            if "semantic_memory" in spec and spec["semantic_memory"] is not None:
                from tinytroupe.agent.memory import SemanticMemory
                human_agent.semantic_memory = SemanticMemory.from_json(spec["semantic_memory"])
        
        if not suppress_mental_state and "_mental_state" in spec:
            human_agent._mental_state = spec["_mental_state"]
        
        # メンタルファカルティは通常不要だが、指定がある場合は復元
        if not suppress_mental_faculties and "_mental_faculties" in spec:
            from tinytroupe.agent.mental_faculty import TinyMentalFaculty
            human_agent._mental_faculties = [
                TinyMentalFaculty.from_json(faculty_json) 
                for faculty_json in spec["_mental_faculties"]
            ]
        
        return human_agent
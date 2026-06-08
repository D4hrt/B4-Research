"""
参加型シミュレーション用ユーティリティ関数
"""

from tinytroupe.agent import TinyPerson
from tinytroupe.agent.participatory_tiny_person import ParticipatoryTinyPerson, HumanIntervention


def convert_to_participatory(person: TinyPerson) -> ParticipatoryTinyPerson:
    """
    TinyPersonをParticipatoryTinyPersonに変換
    
    Args:
        person: 変換元のTinyPerson
    
    Returns:
        ParticipatoryTinyPerson: 変換後のインスタンス
    """
    # 新しいインスタンスを作成（__init__を呼ばない）
    participatory = ParticipatoryTinyPerson.__new__(ParticipatoryTinyPerson)
    
    # 元のTinyPersonの属性をすべてコピー
    participatory.__dict__.update(person.__dict__)
    
    # ParticipatoryTinyPerson固有の属性を初期化
    participatory.human_intervention = HumanIntervention(person.name)
    participatory.training_mode = False
    participatory._force_think_first = False  # GUIDE後にTHINKを強制するフラグ
    
    # エージェントレジストリを更新
    if person.name in TinyPerson.all_agents:
        del TinyPerson.all_agents[person.name]
    TinyPerson.add_agent(participatory)
    
    print(f"✅ {participatory.name} を ParticipatoryTinyPerson に変換しました")
    
    return participatory
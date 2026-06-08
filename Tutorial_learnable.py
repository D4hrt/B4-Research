import os
# APIキーの設定（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

import sys
sys.path.insert(0, '..')

from tinytroupe.agent import TinyPerson
from tinytroupe.agent.learnable_tiny_person import LearnableTinyPerson
from tinytroupe.agent.learnable_utils import convert_to_learnable
from tinytroupe.environment import TinyWorld
from tinytroupe.factory import TinyPersonFactory



factory = TinyPersonFactory(
    context="A planning meeting in a university research laboratory to design a demonstration system for the upcoming Open Campus event"
)

# ========== 1-1. Project Manager（後で訓練対象になる） ==========
pm_base = factory.generate_person(
    """
    Project Manager. 
    Leads meetings and organizes discussions.
    Focuses on goal-setting and prioritization.
    Always confirms feasibility.
    Prefers clear and structured decision-making.
    """
)

print(f"✅ {pm_base.name} を生成しました（通常エージェント）")
pm_trainee = convert_to_learnable(pm_base)

print(f"✅ {pm_trainee.name} をLearnableTinyPersonに変換しました")

# ========== 1-2. Systems Engineer（自律LLMエージェント） ==========
engineer = factory.generate_person(
    """
    Systems Engineer. 
    Responsible for IoT/MCP implementation.
    Focuses on feasibility and technical constraints.
    Proposes specific hardware configurations.
    Pays attention to technical details.
    """
)

print(f"✅ {engineer.name} を生成しました（自律エージェント）")

# ========== 1-3. AI Researcher（自律LLMエージェント） ==========
ai_researcher = factory.generate_person(
    """
    AI Researcher. 
    Focuses on LLM reasoning and MCP research significance.
    Emphasizes educational value and clarity.
    Highlights research novelty.
    Aims for explanations understandable to high school students.
    """
)

print(f"✅ {ai_researcher.name} を生成しました（自律エージェント）")



# ========== 2. エージェント仕様を保存（自律条件で再利用するため） ==========
print("\n" + "="*70)
print("📋 ステップ2: エージェント仕様の保存")
print("="*70)

os.makedirs("./agent_specs", exist_ok=True)

pm_spec_path = "./agent_specs/pm_autonomous.json"
engineer_spec_path = "./agent_specs/engineer_autonomous.json"
ai_researcher_spec_path = "./agent_specs/ai_researcher_autonomous.json"

# ========== 重要: include_memory=False で保存 ==========
# エピソディックメモリを含めないことで、クリーンな状態を保存
pm_base.save_specification(pm_spec_path, include_memory=False)
engineer.save_specification(engineer_spec_path, include_memory=False)
ai_researcher.save_specification(ai_researcher_spec_path, include_memory=False)

print(f"✅ PMエージェントを保存: {pm_spec_path}")
print(f"✅ Engineerエージェントを保存: {engineer_spec_path}")
print(f"✅ AI Researcherエージェントを保存: {ai_researcher_spec_path}")

# ========== 3. 会議トピックの設定 ==========
meeting_topic = """
Let's discuss the design of a smart laboratory demonstration 
for the upcoming Open Campus event.

# Background
Our laboratory has developed an infrastructure integrating 
IoT, LLM, AI, and MCP to operate the entire lab as a "Smart Lab".

# Objective
Design an interactive 10-15 minute demonstration system 
for high school students that showcases the lab's features.

# Demo Requirements
- AI agent explains lab status while controlling IoT devices
- Show integration of IoT sensors/actuators with AI
- Demonstrate multi-source integration using MCP
- Include interactive elements for visitors
- Emphasize lab's uniqueness

# Discussion Flow
Please reach consensus on the following items in order:

1. **Demo Theme**: Determine the core concept
2. **Experience Flow**: How visitors will experience it
3. **Technical Architecture**: IoT + MCP + LLM integration
4. **Role Assignment**: Who does what
5. **Required Resources**: Equipment, budget, personnel, schedule

Let's begin the discussion.
"""

# ========== 5. 訓練セッション開始 ==========
print("\n" + "="*70)
print("🎓 訓練セッション開始")
print("="*70)
print()
print("💡 このセッションでは、Harutoエージェントの行動を訂正できます。")
print("   各行動について、以下の選択肢があります:")
print("   - ACCEPT: そのまま受け入れる")
print("   - MODIFY: 内容を修正する")
print("   - REJECT: 却下して新しい行動を指定")
print("   - EXPLAIN: 問題点を説明して再生成を促す")
print()
print("="*70)
print()

# ========== 9. 参加型条件のシミュレーション ==========
print("\n" + "="*70)
print("🎓 フェーズ2: 参加型条件のシミュレーション（訓練あり）")
print("="*70)
print()
print("💡 このセッションでは、PMエージェントの行動を訂正できます。")
print("   各行動について、以下の選択肢があります:")
print("   - ACCEPT: そのまま受け入れる")
print("   - MODIFY: 内容を修正する")
print("   - REJECT: 却下して新しい行動を指定")
print("   - EXPLAIN: 問題点を説明して再生成を促す")
print()
print("="*70)
print()

# 新しい環境を作成
lab_meeting_participatory = TinyWorld(
    "Research Lab Meeting Room (Participatory)",
    [pm_trainee, engineer, ai_researcher]
)
lab_meeting_participatory.make_everyone_accessible()

# トピックをブロードキャスト
lab_meeting_participatory.broadcast(meeting_topic)

# 訓練モードを有効化
pm_trainee.set_training_mode(True)
print(f"✅ {pm_trainee.name} の訓練モードを有効化しました\n")

# シミュレーション実行（参加型）
print(f"\n{'='*70}")
print(f"📍 参加型条件: シミュレーション実行")
print(f"{'='*70}\n")

lab_meeting_participatory.run(steps=3, randomize_agents_order=True)





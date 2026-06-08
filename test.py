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
from tinytroupe.evaluation import CompleteMeetingEvaluator

import json
from datetime import datetime
import logging


# ========== 1. エージェント作成 ==========
print("\n" + "="*70)
print("📋 ステップ1: エージェント作成（訓練前）")
print("="*70)

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

# ========== 4. 自律条件のシミュレーション ==========
print("\n" + "="*70)
print("🤖 フェーズ1: 自律条件のシミュレーション（訓練なし）")
print("="*70)

# 環境構築（すべて通常のTinyPerson）
lab_meeting_autonomous = TinyWorld(
    "Research Lab Meeting Room (Autonomous)",
    [pm_base, engineer, ai_researcher]
)
lab_meeting_autonomous.make_everyone_accessible()

# トピックをブロードキャスト
lab_meeting_autonomous.broadcast(meeting_topic)
print("✅ 会議トピックをブロードキャストしました")

# 自律シミュレーション実行
print(f"\n{'='*70}")
print(f"📍 自律条件: シミュレーション実行")
print(f"{'='*70}\n")

lab_meeting_autonomous.run(steps=3, randomize_agents_order=True)

# ========== 8. 参加型条件用に保存済みエージェントを再読み込み ==========
print("\n" + "="*70)
print("🔄 フェーズ2準備: 保存済みエージェントを再読み込み")
print("="*70)

# ========== 修正: すべてをクリアして再作成 ==========
# 1. 環境をクリア
lab_meeting_autonomous.remove_all_agents()
print("✅ 環境からすべてのエージェントを削除しました")

# 2. すべてのエージェントをクリア
TinyPerson.clear_agents()
print("✅ すべてのエージェントをクリアしました")
# ========== ここまで修正 ==========

# ========== 重要: 保存したクリーンな仕様から読み込み ==========
pm_restored = TinyPerson.load_specification(pm_spec_path)
engineer_participatory = TinyPerson.load_specification(engineer_spec_path)
ai_researcher_participatory = TinyPerson.load_specification(ai_researcher_spec_path)

print(f"✅ {pm_restored.name} を再読み込み（クリーンな状態）")
print(f"✅ {engineer_participatory.name} を再読み込み（クリーンな状態）")
print(f"✅ {ai_researcher_participatory.name} を再読み込み（クリーンな状態）")

# PMをLearnableTinyPersonに変換
pm_trainee = convert_to_learnable(pm_restored)

print(f"✅ {pm_trainee.name} をLearnableTinyPersonに変換しました")

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
    [pm_trainee, engineer_participatory, ai_researcher_participatory]
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

# 訓練モードを無効化
pm_trainee.set_training_mode(False)
print(f"\n✅ {pm_trainee.name} の訓練モードを無効化しました")

# ========== 10. 学習統計の表示 ==========
print("\n" + "="*70)
print("📊 訓練セッション完了 - 学習統計")
print("="*70)

stats = pm_trainee.get_learning_statistics()

print(f"\n📈 統計情報:")
print(f"  生成された行動数: {stats['actions_generated']}")
print(f"  訂正を受けた回数: {stats['total_corrections_received']}")

if stats['actions_generated'] > 0:
    acceptance_rate = stats.get('acceptance_rate', 0)
    print(f"  訂正なしで受け入れられた率: {acceptance_rate:.1%}")

if stats.get('corrections_by_type'):
    print(f"\n📋 訂正タイプ別内訳:")
    for correction_type, count in stats['corrections_by_type'].items():
        print(f"    {correction_type}: {count}回")

# ========== 11. 学習済みPMエージェントの保存 ==========
pm_trained_path = "../trained_agents/pm_trained.json"
os.makedirs(os.path.dirname(pm_trained_path), exist_ok=True)

pm_trainee.save_learned_specification(pm_trained_path)
print(f"\n💾 学習済みPMエージェントを保存しました: {pm_trained_path}")

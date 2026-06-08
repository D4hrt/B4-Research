"""
test_evaluation_full.py - 評価システムを含む完全なテストスクリプト

このスクリプトは以下を実行します:
1. 自律条件（Autonomous）でシミュレーションを実行
2. 参加型条件（Participatory）でシミュレーションを実行
3. 両条件の評価を実行（ミクロ・マクロ・プロセス指標）
4. 条件間の比較結果を出力

評価シナリオ: Smart Lab Demo Planning Meeting
- オープンキャンパスに向けた「スマート研究室案内デモの設計会議」をシミュレート
- 3名のエージェント（PM、Systems Engineer、AI Researcher）が議論

研究目的（evaluation.mdに基づく）:
- RQ1: Human feedback はエージェント行動の品質を向上させるか？（ミクロ評価）
- RQ2: 自律と参加型でシミュレーション結果はどう異なるか？（マクロ評価）
"""


import os
import sys
from datetime import datetime
import argparse

# APIキーの設定（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

sys.path.insert(0, '..')

from tinytroupe.agent import TinyPerson
from tinytroupe.agent.participatory_tiny_person import ParticipatoryTinyPerson
from tinytroupe.agent.participatory_utils import convert_to_participatory
from tinytroupe.environment import TinyWorld
from tinytroupe.evaluation import MeetingEvaluator


# ============================================================================
# 設定
# ============================================================================

# コマンドライン引数でステップ数指定
parser = argparse.ArgumentParser(description="TinyTroupe Full Evaluation Test")
parser.add_argument('--steps', type=int, default=10, help='Number of simulation steps (default: 10)')
args, unknown = parser.parse_known_args()

SIMULATION_STEPS = args.steps  # シミュレーションステップ数（本評価用）
SAMPLE_SIZE_PER_AGENT = 5  # 各エージェントから評価するアクション数
EVALUATION_MODEL = "gpt-4o-mini"  # 評価に使用するモデル（コスト削減のためmini）

# agent_specsディレクトリのパス
PM_SPEC_PATH = "./agent_specs/pm_participatory.json"
ENGINEER_SPEC_PATH = "./agent_specs/engineer_participatory.json"
AI_RESEARCHER_SPEC_PATH = "./agent_specs/ai_researcher_participatory.json"


# ============================================================================
# 会議トピック（目的明示・手段暗黙アプローチ）
# ============================================================================
MEETING_TOPIC = """
Design an interactive demonstration for high school students 
that showcases our Smart Lab capabilities.

# Background
Our laboratory has developed an infrastructure integrating 
IoT, LLM, AI, and MCP to operate the entire lab as a "Smart Lab".
The Open Campus event is coming up, and we need to prepare 
a compelling demonstration.

# Requirements
- Duration: 10-15 minutes
- Must be engaging and educational for high school visitors
- Should highlight the integration of IoT devices with AI
- Needs to be feasible with our current resources

Let's begin the discussion.
"""


# ============================================================================
# ヘルパー関数
# ============================================================================
def load_agents():
    """エージェントをロード"""
    print("\n" + "="*70)
    print("📋 エージェントをロード")
    print("="*70)
    
    pm = TinyPerson.load_specification(PM_SPEC_PATH)
    engineer = TinyPerson.load_specification(ENGINEER_SPEC_PATH)
    ai_researcher = TinyPerson.load_specification(AI_RESEARCHER_SPEC_PATH)
    
    print(f"✅ {pm.name} をロードしました（Project Manager）")
    print(f"✅ {engineer.name} をロードしました（Systems Engineer）")
    print(f"✅ {ai_researcher.name} をロードしました（AI Researcher）")
    
    return pm, engineer, ai_researcher


def run_autonomous_simulation():
    """
    自律条件（Autonomous）でシミュレーションを実行
    
    Returns:
        tuple: (world, agents) - シミュレーション後のワールドとエージェントリスト
    """
    print("\n" + "="*70)
    print("🤖 自律条件（Autonomous）シミュレーション開始")
    print("="*70)
    print()
    print("   このシミュレーションでは人間の介入なしに")
    print("   エージェントが自律的に議論を進めます。")
    print()
    
    # エージェントレジストリをクリア（前回の実行が残っている場合に対応）
    TinyPerson.all_agents.clear()
    
    # エージェントをロード（新しいインスタンス）
    pm, engineer, ai_researcher = load_agents()
    agents = [pm, engineer, ai_researcher]
    
    # 環境を作成
    meeting_world = TinyWorld(
        "Research Lab Meeting Room (Autonomous)",
        agents
    )
    meeting_world.make_everyone_accessible()
    
    # 会議トピックをブロードキャスト
    meeting_world.broadcast(MEETING_TOPIC)
    print("✅ 会議トピックをブロードキャストしました")
    
    # シミュレーション実行
    print(f"\n📍 シミュレーション実行中... ({SIMULATION_STEPS} steps)")
    meeting_world.run(steps=SIMULATION_STEPS, randomize_agents_order=True)
    
    print("\n✅ 自律条件シミュレーション完了")
    print(f"   総発話数: {len(meeting_world._displayed_communications_buffer)}")
    # 保存: 整形済トランスクリプトをファイルに出力
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    condition = "autonomous"
    os.makedirs("simulation_results", exist_ok=True)
    world_path = os.path.join("simulation_results", f"{condition}_{ts}.txt")
    with open(world_path, "w", encoding="utf-8") as fh:
        fh.write(meeting_world.pretty_current_interactions(max_content_length=None, first_n=None, last_n=None))

    # 各エージェントごとのトランスクリプトを保存
    agents_dir = os.path.join("simulation_results", "agents_results")
    os.makedirs(agents_dir, exist_ok=True)
    for ag in agents:
        safe_name = ag.name.replace(" ", "_")
        a_path = os.path.join(agents_dir, f"{condition}_{safe_name}_{ts}.txt")
        with open(a_path, "w", encoding="utf-8") as af:
            af.write(ag.pretty_current_interactions(max_content_length=None, first_n=None, last_n=None))

    print(f"\n💾 シミュレーションログを保存しました: {world_path}")
    return meeting_world, agents


def run_participatory_simulation():
    """
    参加型条件（Participatory）でシミュレーションを実行
    
    PMエージェントに対して人間が介入可能。
    
    Returns:
        tuple: (world, agents) - シミュレーション後のワールドとエージェントリスト
    """
    print("\n" + "="*70)
    print("👤 参加型条件（Participatory）シミュレーション開始")
    print("="*70)
    print()
    print("💡 このセッションでは、PMエージェントの行動に介入できます。")
    print()
    print("   介入オプション:")
    print("   ┌────────────────────────────────────────────────────────────┐")
    print("   │  ACCEPT (Enter) - この行動を承認                           │")
    print("   │  GUIDE          - ガイドラインを追加して再生成              │")
    print("   └────────────────────────────────────────────────────────────┘")
    print()
    print("   GUIDEの例:")
    print("   - 「今はデモテーマの議論に集中すること」")
    print("   - 「技術的詳細はエンジニアに委ねること」")
    print("   - 「全員の意見を聞いてから次の議題に移ること」")
    print()
    
    # エージェントレジストリをクリア（自律条件のエージェントが残っている場合に対応）
    TinyPerson.all_agents.clear()
    
    # エージェントをロード（新しいインスタンス）
    pm_base, engineer, ai_researcher = load_agents()
    
    # PMを参加型エージェントに変換
    pm_participatory = convert_to_participatory(pm_base)
    
    agents = [pm_participatory, engineer, ai_researcher]
    
    # 環境を作成
    meeting_world = TinyWorld(
        "Research Lab Meeting Room (Participatory)",
        agents
    )
    meeting_world.make_everyone_accessible()
    
    # 会議トピックをブロードキャスト
    meeting_world.broadcast(MEETING_TOPIC)
    print("✅ 会議トピックをブロードキャストしました")
    
    # PMの訓練モード（人間介入モード）を有効化
    pm_participatory.set_training_mode(True)
    print(f"✅ {pm_participatory.name} の参加型モードを有効化しました\n")
    
    # シミュレーション実行
    print(f"\n📍 シミュレーション実行中... ({SIMULATION_STEPS} steps)")
    meeting_world.run(steps=SIMULATION_STEPS, randomize_agents_order=True)
    
    # 介入統計を表示
    print("\n" + "-"*70)
    pm_participatory.print_intervention_summary()
    
    print("\n✅ 参加型条件シミュレーション完了")
    print(f"   総発話数: {len(meeting_world._displayed_communications_buffer)}")
    # 保存: 整形済トランスクリプトをファイルに出力
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    condition = "participatory"
    os.makedirs("simulation_results", exist_ok=True)
    world_path = os.path.join("simulation_results", f"{condition}_{ts}.txt")
    with open(world_path, "w", encoding="utf-8") as fh:
        fh.write(meeting_world.pretty_current_interactions(max_content_length=None, first_n=None, last_n=None))

    # 各エージェントごとのトランスクリプトを保存
    agents_dir = os.path.join("simulation_results", "agents_results")
    os.makedirs(agents_dir, exist_ok=True)
    for ag in agents:
        safe_name = ag.name.replace(" ", "_")
        a_path = os.path.join(agents_dir, f"{condition}_{safe_name}_{ts}.txt")
        with open(a_path, "w", encoding="utf-8") as af:
            af.write(ag.pretty_current_interactions(max_content_length=None, first_n=None, last_n=None))

    print(f"\n💾 シミュレーションログを保存しました: {world_path}")
    return meeting_world, agents


def print_simulation_summary(world: TinyWorld, condition_name: str):
    """シミュレーションのサマリーを表示"""
    print(f"\n{'='*70}")
    print(f"📝 {condition_name} 発言履歴")
    print(f"{'='*70}")
    


# ============================================================================
# メイン実行
# ============================================================================
def main():
    """メイン実行関数"""
    print("\n" + "="*70)
    print("🎓 評価システムを含む完全テスト")
    print("="*70)
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"シミュレーションステップ数: {SIMULATION_STEPS}")
    print(f"評価サンプルサイズ: {SAMPLE_SIZE_PER_AGENT} per agent")
    print(f"評価モデル: {EVALUATION_MODEL}")
    print("="*70)
    
    # 評価器を初期化
    evaluator = MeetingEvaluator(
        model=EVALUATION_MODEL,
        sample_size_per_agent=SAMPLE_SIZE_PER_AGENT
    )
    
    # ========================================================================
    # 1. 自律条件のシミュレーション
    # ========================================================================
    auto_world, auto_agents = run_autonomous_simulation()
    
    # 自律条件の評価
    print("\n" + "="*70)
    print("📊 自律条件の評価を実行")
    print("="*70)
    
    auto_report = evaluator.evaluate_simulation(
        world=auto_world,
        agents=auto_agents,
        meeting_topic=MEETING_TOPIC,
        condition_name="autonomous"
    )
    
    # 評価結果を保存
    auto_filepath = evaluator.save_evaluation_report(auto_report)
    
    # ========================================================================
    # 2. 参加型条件のシミュレーション
    # ========================================================================
    part_world, part_agents = run_participatory_simulation()
    
    # 参加型条件の評価
    print("\n" + "="*70)
    print("📊 参加型条件の評価を実行")
    print("="*70)
    
    part_report = evaluator.evaluate_simulation(
        world=part_world,
        agents=part_agents,
        meeting_topic=MEETING_TOPIC,
        condition_name="participatory"
    )
    
    # 評価結果を保存
    part_filepath = evaluator.save_evaluation_report(part_report)
    
    # ========================================================================
    # 3. 条件間の比較
    # ========================================================================
    print("\n" + "="*70)
    print("📈 条件間の比較分析")
    print("="*70)
    
    comparison = evaluator.compare_conditions(auto_report, part_report)
    evaluator.print_comparison_summary(comparison)
    
    # 比較結果を保存
    import json
    comparison_path = f"./evaluation_results/comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("./evaluation_results", exist_ok=True)
    with open(comparison_path, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n💾 比較結果を保存しました: {comparison_path}")
    
    # ========================================================================
    # 4. 最終サマリー
    # ========================================================================
    print("\n" + "="*70)
    print("🎯 テスト完了サマリー")
    print("="*70)
    print()
    print("📋 実行した評価:")
    print("   1. ミクロ評価（LLM-as-a-judge）")
    print("      - Persona Consistency")
    print("      - Logical Consistency")
    print("      - Task Adherence")
    print()
    print("   2. マクロ評価（ハイブリッド）")
    print("      - 成果物抽出（ResultsExtractor）")
    print("      - 成果物品質評価（LLM）")
    print("      - 矛盾検出（LLM）")
    print("      - 合意形成判定（LLM）")
    print()
    print("   3. プロセス指標（LLM不使用）")
    print("      - ターン数")
    print("      - 停滞率")
    print("      - 発散回数")
    print()
    print("📁 出力ファイル:")
    print(f"   - 自律条件評価: {auto_filepath}")
    print(f"   - 参加型条件評価: {part_filepath}")
    print(f"   - 比較結果: {comparison_path}")
    print()
    print("="*70)
    print(f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    return auto_report, part_report, comparison


if __name__ == "__main__":
    # 対話型入力を促す
    print("\n" + "="*70)
    print("⚠️  実行前の確認")
    print("="*70)
    print()
    print("このテストは以下を実行します:")
    print("  1. 自律条件シミュレーション（自動）")
    print("  2. 参加型シミュレーション（対話あり）")
    print("  3. 両条件の評価と比較")
    print()
    print("参加型シミュレーションでは、PMエージェントの行動に対して")
    print("ACCEPT/GUIDEの入力を求められます。")
    print()
    
    response = input("続行しますか？ [Y/n]: ").strip().lower()
    if response in ('', 'y', 'yes'):
        main()
    else:
        print("テストをキャンセルしました。")

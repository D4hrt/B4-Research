"""
Tutorial_participatory.py - 参加型シミュレーションのテスト

このスクリプトは参加型LLMマルチエージェントシミュレーションの実装をテストします。

評価シナリオ: Smart Lab Demo Planning Meeting
- オープンキャンパスに向けた「スマート研究室案内デモの設計会議」をシミュレート
- 3名のエージェント（PM、Systems Engineer、AI Researcher）が議論

参加型シミュレーションの特徴:
- ACCEPT: 行動を承認
- GUIDE: ガイドラインを追加して再生成（永続的効果）

研究目的:
- 長期的な行動の一貫性の改善
- 役割からの逸脱防止
- 議論の停滞防止

ガイドライン設計（Working Memory）:
- 人間からの指示は「作業記憶」としてプロンプトに注入
- 認知科学的に適切：目標維持機能（goal maintenance）を含む
- TinyTroupeの他のメモリ機構（Episodic/Semantic Memory）と整合
- メタ的反応（「ご指摘ありがとうございます」等）はプロンプトで明示的に抑制
- ガイドラインは後続の全ての行動生成に永続的に影響
- 多様な種類の情報を統一的に扱える:
  ✅ 合意事項: "AGREED: Demo Theme 'Smart Lab Voice Assistant'"
  ✅ 制約条件: "Available hardware: temperature sensor, CO2 sensor"
  ✅ 成果物リスト: "Required Deliverables: 1. Demo Theme, 2. Experience Flow..."
  ✅ 行動指針: "Be specific with technical details"
- 注意: 一時的な深掘り指示（「センサーについて詳しく」）は永続化するため固執の原因に
"""

import os
import sys
from datetime import datetime

# APIキーの設定（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

sys.path.insert(0, '..')

from tinytroupe.agent import TinyPerson
from tinytroupe.agent.participatory_tiny_person import ParticipatoryTinyPerson
from tinytroupe.agent.participatory_utils import convert_to_participatory
from tinytroupe.environment import TinyWorld
from tinytroupe.evaluation import MeetingEvaluator


# ============================================================================
# 1. 保存済みエージェントのロード
# ============================================================================
print("\n" + "="*70)
print("📋 ステップ1: 保存済みエージェントをロード")
print("="*70)

pm_spec_path = "./agent_specs/pm_participatory.json"
engineer_spec_path = "./agent_specs/engineer_participatory.json"
ai_researcher_spec_path = "./agent_specs/ai_researcher_participatory.json"

# 保存済みのペルソナをロード
pm_base = TinyPerson.load_specification(pm_spec_path)
engineer = TinyPerson.load_specification(engineer_spec_path)
ai_researcher = TinyPerson.load_specification(ai_researcher_spec_path)

print(f"✅ {pm_base.name} をロードしました（Project Manager）")
print(f"✅ {engineer.name} をロードしました（Systems Engineer）")
print(f"✅ {ai_researcher.name} をロードしました（AI Researcher）")


# ============================================================================
# 2. 会議トピックの設定（目的明示・手段暗黙アプローチ）
# ============================================================================
meeting_topic = """
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
# 4. PMをParticipatoryTinyPersonに変換
# ============================================================================
print("\n" + "="*70)
print("📋 ステップ2: PMを参加型エージェントに変換")
print("="*70)

pm_participatory = convert_to_participatory(pm_base)


# ============================================================================
# 5. 参加型シミュレーションの実行
# ============================================================================
print("\n" + "="*70)
print("🎓 参加型シミュレーション開始")
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
print("   GUIDEの例（Facilitator Notes）:")
print("   - 合意事項: \"AGREED: Demo Theme 'Smart Lab Voice Assistant'\"")
print("   - 制約条件: \"Available hardware: temperature sensor, CO2 sensor\"")
print("   - 成果物: \"Required Deliverables: 1. Theme, 2. Flow, 3. Tech Design\"")
print("   - 行動指針: \"Be specific with technical details\"")
print()
print("="*70)
print()

# 環境を作成
lab_meeting = TinyWorld(
    "Research Lab Meeting Room (Participatory)",
    [pm_participatory, engineer, ai_researcher]
)
lab_meeting.make_everyone_accessible()

# 会議トピックをブロードキャスト
lab_meeting.broadcast(meeting_topic)
print("✅ 会議トピックをブロードキャストしました")

# PMの訓練モード（人間介入モード）を有効化
pm_participatory.set_training_mode(True)
print(f"✅ {pm_participatory.name} の参加型モードを有効化しました\n")

# シミュレーション実行
print(f"\n{'='*70}")
print(f"📍 シミュレーション開始: 参加型条件")
print(f"{'='*70}\n")

# 会議の議論を観察しながら、必要に応じてPMにガイドラインを追加
SIMULATION_STEPS = 2

lab_meeting.run(steps=SIMULATION_STEPS, randomize_agents_order=True)


# ============================================================================
# 6. 結果サマリー
# ============================================================================
print("\n" + "="*70)
print("📊 シミュレーション結果サマリー")
print("="*70)

# PMの介入統計を表示
pm_participatory.print_intervention_summary()

# 通信バッファの内容を確認
print("\n📝 会議の発言履歴:")
print("-"*70)
for i, comm in enumerate(lab_meeting._displayed_communications_buffer, 1):
    if comm.get("action"):
        action = comm["action"]
        agent_name = comm.get("source", "Unknown")
        action_type = action.get("type", "Unknown")
        content = action.get("content", "")[:100]  # 最初の100文字
        print(f"{i}. [{agent_name}] ({action_type}): {content}...")
print("-"*70)

# 統計情報
stats = pm_participatory.get_intervention_statistics()
print(f"\n📈 介入統計:")
print(f"   - 総介入回数: {stats['total']}")
print(f"   - ACCEPT回数: {stats['by_type'].get('ACCEPT', 0)}")
print(f"   - GUIDE回数: {stats['by_type'].get('GUIDE', 0)}")
print(f"   - 蓄積ガイドライン数: {stats['guidelines_count']}")

if stats['guidelines']:
    print(f"\n📋 蓄積されたガイドライン:")
    for i, g in enumerate(stats['guidelines'], 1):
        print(f"   {i}. {g}")


# ============================================================================
# 7. 評価の実行
# ============================================================================
print("\n" + "="*70)
print("🔍 評価フェーズ")
print("="*70)

# 評価を実行するか確認
run_evaluation = input("\n評価を実行しますか？ [y/N]: ").strip().lower()

if run_evaluation == 'y':
    print("\n📊 評価を開始します...")
    
    # エージェントリストを作成
    agents = [pm_participatory, engineer, ai_researcher]
    
    # 評価器を初期化（コスト削減のためgpt-4o-miniを使用）
    evaluator = MeetingEvaluator(
        model="gpt-4o-mini",
        sample_size_per_agent=3  # テスト用に少なめ
    )
    
    # 評価実行
    try:
        report = evaluator.evaluate_simulation(
            world=lab_meeting,
            agents=agents,
            meeting_topic=meeting_topic,
            condition_name="participatory_test"
        )
        
        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = evaluator.save_evaluation_report(
            report, 
            output_dir="./evaluation_results"
        )
        print(f"\n✅ 評価レポートを保存: {report_path}")
        
        # サマリー表示
        print("\n" + "="*70)
        print("📈 評価サマリー")
        print("="*70)
        
        if 'summary' in report:
            summary = report['summary']
            print(f"\n【総合評価】")
            if 'overall_quality' in summary:
                print(f"   総合品質: {summary['overall_quality']}")
            if 'recommendation' in summary:
                print(f"   推奨事項: {summary['recommendation']}")
        
        if 'micro' in report and 'aggregate' in report['micro']:
            agg = report['micro']['aggregate']
            print(f"\n【ミクロ評価（行動品質）】")
            print(f"   Persona Consistency: {agg.get('persona_consistency_avg', 'N/A'):.2f}")
            print(f"   Logical Consistency: {agg.get('logical_consistency_avg', 'N/A'):.2f}")
            print(f"   Task Adherence:      {agg.get('task_adherence_avg', 'N/A'):.2f}")
        
        if 'process' in report:
            proc = report['process']
            print(f"\n【プロセス指標】")
            print(f"   総ターン数: {proc.get('total_turns', 'N/A')}")
            if 'stagnation' in proc:
                print(f"   停滞率: {proc['stagnation'].get('rate', 'N/A'):.1%}")
            if 'divergence' in proc:
                print(f"   発散回数: {proc['divergence'].get('count', 'N/A')}")
                
    except Exception as e:
        print(f"\n❌ 評価中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n⏭️ 評価をスキップしました")

print("\n" + "="*70)
print("✅ シミュレーション完了")
print("="*70)


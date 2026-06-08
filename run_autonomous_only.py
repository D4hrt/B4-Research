"""
run_autonomous_only.py - 自律条件のみのシミュレーション実行

参加型条件（対話あり）を除外し、自律条件のみを実行・評価します。
洗練されたペルソナを使用する場合は --spec-dir オプションで指定可能。

使い方:
    # オリジナルペルソナで実行
    python run_autonomous_only.py

    # 参加型履歴から洗練されたペルソナで実行
    python run_autonomous_only.py --spec-dir ./agent_specs/refined_from_participatory_20260227_133610

    # 自律型履歴から洗練されたペルソナで実行
    python run_autonomous_only.py --spec-dir ./agent_specs/refined_from_autonomous_20260227_133813

    # 条件ラベルを指定（保存ファイル名に使用）
    python run_autonomous_only.py --spec-dir ./agent_specs/refined_from_participatory_20260227_133610 --label refined_participatory
"""

import os
import sys
import argparse
from datetime import datetime

# APIキーの設定（環境変数 OPENAI_API_KEY を事前に設定してください）
assert os.environ.get("OPENAI_API_KEY"), "環境変数 OPENAI_API_KEY が設定されていません"

sys.path.insert(0, '..')

from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
from tinytroupe.evaluation import MeetingEvaluator


# ============================================================================
# コマンドライン引数
# ============================================================================
parser = argparse.ArgumentParser(
    description="自律条件シミュレーション（洗練ペルソナ対応）",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument(
    "--spec-dir", type=str, default=None,
    help="洗練済みペルソナのディレクトリ（省略時はオリジナルを使用）",
)
parser.add_argument(
    "--label", type=str, default=None,
    help="条件ラベル（保存ファイル名に使用。省略時は自動決定）",
)
parser.add_argument(
    "--steps", type=int, default=10,
    help="シミュレーションステップ数（デフォルト: 10）",
)
args, _unknown = parser.parse_known_args()


# ============================================================================
# 設定
# ============================================================================
SIMULATION_STEPS = args.steps  # シミュレーションステップ数
SAMPLE_SIZE_PER_AGENT = 5  # 各エージェントから評価するアクション数
EVALUATION_MODEL = "gpt-4o-mini"  # 評価に使用するモデル

# agent_specsディレクトリのパス（--spec-dir で上書き可能）
if args.spec_dir:
    _dir = args.spec_dir.rstrip("/")
    PM_SPEC_PATH = f"{_dir}/pm_participatory.json"
    ENGINEER_SPEC_PATH = f"{_dir}/engineer_participatory.json"
    AI_RESEARCHER_SPEC_PATH = f"{_dir}/ai_researcher_participatory.json"
else:
    PM_SPEC_PATH = "./agent_specs/pm_participatory.json"
    ENGINEER_SPEC_PATH = "./agent_specs/engineer_participatory.json"
    AI_RESEARCHER_SPEC_PATH = "./agent_specs/ai_researcher_participatory.json"

# 条件ラベル（ファイル名に使用）
if args.label:
    CONDITION_LABEL = args.label
elif args.spec_dir:
    # ディレクトリ名から自動決定  e.g. "refined_from_participatory_20260227_133610" -> "refined_participatory"
    dirname = os.path.basename(args.spec_dir.rstrip("/"))
    if "refined_from_participatory" in dirname:
        CONDITION_LABEL = "refined_participatory"
    elif "refined_from_autonomous" in dirname:
        CONDITION_LABEL = "refined_autonomous"
    else:
        CONDITION_LABEL = dirname
else:
    CONDITION_LABEL = "autonomous"


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

# Your Task
Discuss and reach consensus on a concrete implementation plan.
Determine what to demonstrate, how to structure the experience,
and what resources will be needed.

Let's begin the discussion.
"""


def load_agents():
    """エージェントをロード"""
    # エージェントレジストリをクリア（名前衝突を防ぐ）
    TinyPerson.all_agents.clear()
    
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
    """自律条件でシミュレーションを実行"""
    print("\n" + "="*70)
    print(f"🤖 自律条件シミュレーション開始 [{CONDITION_LABEL}]")
    print("="*70)
    print(f"   ペルソナ: {PM_SPEC_PATH}")
    
    pm, engineer, ai_researcher = load_agents()
    agents = [pm, engineer, ai_researcher]
    
    # 会議環境を作成
    meeting_world = TinyWorld(
        name=f"Smart Lab Demo Planning Meeting ({CONDITION_LABEL})",
        agents=agents
    )
    meeting_world.make_everyone_accessible()
    
    # 会議トピックを全員にブロードキャスト
    meeting_world.broadcast(MEETING_TOPIC)
    
    # シミュレーション実行
    print(f"\n🔄 シミュレーション実行中... ({SIMULATION_STEPS}ステップ)")
    meeting_world.run(steps=SIMULATION_STEPS, randomize_agents_order=True)
    
    print("\n✅ 自律条件シミュレーション完了")
    print(f"   総発話数: {len(meeting_world._displayed_communications_buffer)}")
    
    # ====================================================================
    # シミュレーション履歴を保存
    # ====================================================================
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("simulation_results", exist_ok=True)
    
    # ワールド全体のトランスクリプト
    world_path = os.path.join(
        "simulation_results", f"{CONDITION_LABEL}_{ts}.txt"
    )
    with open(world_path, "w", encoding="utf-8") as fh:
        fh.write(meeting_world.pretty_current_interactions(
            max_content_length=None, first_n=None, last_n=None
        ))
    
    # 各エージェントごとのトランスクリプト
    agents_dir = os.path.join("simulation_results", "agents_results")
    os.makedirs(agents_dir, exist_ok=True)
    for ag in agents:
        safe_name = ag.name.replace(" ", "_")
        a_path = os.path.join(
            agents_dir, f"{CONDITION_LABEL}_{safe_name}_{ts}.txt"
        )
        with open(a_path, "w", encoding="utf-8") as af:
            af.write(ag.pretty_current_interactions(
                max_content_length=None, first_n=None, last_n=None
            ))
    
    print(f"\n💾 シミュレーションログを保存しました:")
    print(f"   ワールド: {world_path}")
    print(f"   エージェント: {agents_dir}/{CONDITION_LABEL}_*_{ts}.txt")
    
    return meeting_world, agents


def print_simulation_summary(world: TinyWorld):
    """シミュレーションのサマリーを表示"""
    print(f"\n{'='*70}")
    print(f"📝 発言履歴（最初の15件）")
    print(f"{'='*70}")
    
    for i, comm in enumerate(world._displayed_communications_buffer[:15], 1):
        if comm.get("action"):
            action = comm["action"]
            agent_name = comm.get("source", "Unknown")
            action_type = action.get("type", "Unknown")
            content = action.get("content", "")[:100]  # 最初の100文字
            print(f"\n{i}. [{agent_name}] ({action_type}):")
            print(f"   {content}...")
    
    if len(world._displayed_communications_buffer) > 15:
        print(f"\n   ... 他 {len(world._displayed_communications_buffer) - 15} 件の発話")


def main():
    """メイン実行関数"""
    print("\n" + "="*70)
    print("🎓 自律条件シミュレーション & 評価")
    print("="*70)
    print(f"開始時刻:           {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"条件ラベル:         {CONDITION_LABEL}")
    print(f"ペルソナディレクトリ: {os.path.dirname(PM_SPEC_PATH)}")
    print(f"ステップ数:         {SIMULATION_STEPS}")
    print(f"評価サンプルサイズ:  {SAMPLE_SIZE_PER_AGENT} per agent")
    print(f"評価モデル:         {EVALUATION_MODEL}")
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
    print_simulation_summary(auto_world)
    
    # ========================================================================
    # 2. 自律条件の評価
    # ========================================================================
    print("\n" + "="*70)
    print("📊 自律条件の評価開始")
    print("="*70)
    
    auto_report = evaluator.evaluate_simulation(
        world=auto_world,
        agents=auto_agents,
        meeting_topic=MEETING_TOPIC,
        condition_name=CONDITION_LABEL
    )
    
    # 評価レポートを保存
    auto_report_path = evaluator.save_evaluation_report(auto_report)
    
    # ========================================================================
    # 3. 結果サマリーを表示
    # ========================================================================
    print("\n" + "="*70)
    print("📈 評価結果サマリー")
    print("="*70)
    
    summary = auto_report["summary"]
    print(f"\n【ミクロ評価】")
    print(f"  Persona Consistency:  {summary['persona_consistency']:.2f}")
    print(f"  Logical Consistency:  {summary['logical_consistency']:.2f}")
    print(f"  Task Adherence:       {summary['task_adherence']:.2f}")
    
    print(f"\n【マクロ評価】")
    print(f"  合意形成:             {'成功' if summary['consensus_success'] else '失敗'}")
    print(f"  成果物品質:           {summary['overall_quality']}")
    print(f"  矛盾件数:             {summary['contradiction_count']}")
    
    print(f"\n【プロセス指標】")
    print(f"  ターン数:             {summary['turns_to_consensus']}")
    print(f"  停滞率:               {summary['stagnation_rate']:.2%}")
    print(f"  発散回数:             {summary['divergence_count']}")
    print(f"  効率性評価:           {summary['efficiency_rating']}")
    
    print(f"\n💾 レポート保存先: {auto_report_path}")
    print(f"\n✅ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

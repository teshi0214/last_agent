# deploy.py - Google Scholar Agent Deployment (修正版)

import os
import vertexai
from absl import app, flags
from dotenv import load_dotenv
# インポートパス修正: academic_researchではなくgoogle_scholar_02パッケージからroot_agentを読み込む
from google_scholar_02.agent import root_agent

from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

import re
import shlex
import subprocess

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")
flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")

flags.DEFINE_bool("list", False, "List all agents.")
flags.DEFINE_bool("create", False, "Create a new agent.")
flags.DEFINE_bool("delete", False, "Delete an existing agent.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete"])

def create() -> None:
    """Creates an agent engine for Academic Research (Google Scholar) Agent."""
    # エージェントをAdkAppでラップしてAgent Engineに対応させる
    adk_app = AdkApp(agent=root_agent, enable_tracing=True)
    # Agent Engine上にエージェントを作成
    try:
        remote_agent = agent_engines.create(
            agent_engine=adk_app,
            display_name=root_agent.name,
            requirements=[
                # 依存ライブラリ: 最新の安定版を許容
                "google-adk>=0.0.2,<2.0.0",
                "google-cloud-aiplatform[agent_engines,adk]>=1.111.0",  # 例: 1.112.0+ 実績
                "google-genai>=1.5.0,<2.0.0",
                "pydantic>=2.10.6,<3.0.0",
                "absl-py>=2.2.1,<3.0.0",
                # ↓ 実行時に agent が import する可能性のある依存を追加（ビルド後の起動失敗を防ぐ）
                "beautifulsoup4>=4.12.0,<5.0.0",
                "lxml>=4.9.0,<6.0.0",
                "requests>=2.31.0,<3.0.0",
                "pandas>=2.0.0,<3.0.0",
                # cloudpickle はSDK側が要求するため固定化
                "cloudpickle==3.1.1",
            ],
            # ローカルのエージェントコードをパッケージに含める
            extra_packages=["google_scholar_02"],  # パッケージ本体のみをアップロード（サイズ削減のため）
        )
        print(f"Created remote agent: {remote_agent.resource_name}")
        return remote_agent
    except Exception as e:
        print("Create failed:", e)
        # エラーメッセージから ReasoningEngine RID を抽出
        m = re.search(r"reasoningEngines/(\\d+)", str(e))
        rid = m.group(1) if m else None
        if rid:
            print("RID (from error) =", rid)
            _dump_re_logs(os.getenv("GOOGLE_CLOUD_PROJECT") or "", os.getenv("GOOGLE_CLOUD_LOCATION") or "", rid)
        else:
            print("RID not found in error. Fetching recent logs without RID filter...")
            _dump_re_logs_no_rid(os.getenv("GOOGLE_CLOUD_PROJECT") or "", os.getenv("GOOGLE_CLOUD_LOCATION") or "")
        raise

def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")

def list_agents() -> None:
    remote_agents = agent_engines.list()
    template = """
{agent.name} ("{agent.display_name}")
- Create time: {agent.create_time}
- Update time: {agent.update_time}
"""
    remote_agents_str = "\n".join(template.format(agent=agent) for agent in remote_agents)
    print(f"All remote agents:\n{remote_agents_str}")

def _dump_re_logs(project: str, region: str, rid: str, freshness: str = "1h", limit: int = 200) -> None:
    if not project or not region or not rid:
        print("Missing project/region/rid for log fetch.")
        return
    kinds = ["stderr", "stdout", "builder"]
    for k in kinds:
        print(f"===== {k} (RID={rid}) =====")
        query = (
            f'logName="projects/{project}/logs/aiplatform.googleapis.com%2Freasoning_engine_{k}" '
            f'AND resource.type="aiplatform.googleapis.com/ReasoningEngine" '
            f'AND resource.labels.location="{region}" '
            f'AND resource.labels.reasoning_engine_id="{rid}"'
        )
        cmd = [
            "gcloud", "logging", "read", query,
            f"--project={project}",
            f"--freshness={freshness}",
            f"--limit={limit}",
            "--order=desc",
            "--format=value(timestamp,severity,resource.labels.reasoning_engine_id,textPayload,jsonPayload.message,protoPayload.line.message)",
        ]
        try:
            print(">>>", " ".join(shlex.quote(c) for c in cmd))
            out = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if out.stdout:
                print(out.stdout.strip())
            if out.stderr:
                print("! STDERR from gcloud:", out.stderr.strip())
        except FileNotFoundError:
            print("gcloud not found. Ensure gcloud CLI is installed and on PATH.")

def _dump_re_logs_no_rid(project: str, region: str, freshness: str = "1h", limit: int = 200) -> None:
    kinds = ["stderr", "stdout", "builder"]
    for k in kinds:
        print(f"===== {k} (no RID filter) =====")
        query = (
            f'logName="projects/{project}/logs/aiplatform.googleapis.com%2Freasoning_engine_{k}" '
            f'AND resource.type="aiplatform.googleapis.com/ReasoningEngine" '
            f'AND resource.labels.location="{region}"'
        )
        cmd = [
            "gcloud", "logging", "read", query,
            f"--project={project}",
            f"--freshness={freshness}",
            f"--limit={limit}",
            "--order=desc",
            "--format=value(timestamp,severity,resource.labels.reasoning_engine_id,textPayload,jsonPayload.message,protoPayload.line.message)",
        ]
        try:
            print(">>>", " ".join(shlex.quote(c) for c in cmd))
            out = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if out.stdout:
                print(out.stdout.strip())
            if out.stderr:
                print("! STDERR from gcloud:", out.stderr.strip())
        except FileNotFoundError:
            print("gcloud not found. Ensure gcloud CLI is installed and on PATH.")

def main(argv: list[str]) -> None:
    del argv  # 未使用引数の破棄
    load_dotenv()

    # 環境変数またはフラグからGCP設定を取得
    project_id = FLAGS.project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    location  = FLAGS.location  or os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket    = FLAGS.bucket    or os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")

    # 必須項目のチェック
    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    if not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    if not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return

    # Vertex AI初期化
    vertexai.init(project=project_id, location=location, staging_bucket=f"gs://{bucket}")

    # デバッグ: パッケージング対象の確認
    print("Packaging current repo with extra_packages=[\"google_scholar_02\"]")

    # フラグに応じて処理を実行
    if FLAGS.list:
        list_agents()
    elif FLAGS.create:
        create()
    elif FLAGS.delete:
        if not FLAGS.resource_id:
            print("resource_id is required for delete")
            return
        delete(FLAGS.resource_id)
    else:
        print("Unknown command or no action specified")

if __name__ == "__main__":
    app.run(main)
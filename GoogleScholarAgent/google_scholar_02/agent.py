"""Academic_Research: A multi-agent system for finding scholarly articles, news,
and author information."""

from google.adk.agents import LlmAgent

test_agent = LlmAgent(
    name="google_scholar_agent",
    instruction="あなたはGoogle Scholar検索をサポートするエージェントです。",
    tools=[],
)
from google.adk.tools import google_search
from google.adk.tools import agent_tool

from . import prompt
from .tools.find_papers import find_papers_tool
from .tools.find_news import find_news_tool
from .tools.find_author import find_author_tool
from .tools.find_author_details import find_author_details_tool
from .settings import Settings

MODEL = "gemini-2.5-pro"


google_search_agent = LlmAgent(
    name="google_search_agent",
    model=MODEL,
    description=(
        "An agent that performs a general Google search when an author's "
        "Google Scholar profile cannot be found."
    ),
    # ※ ADKのこのバージョンは instructions ではなく instruction を使用
    instruction=(
        "あなたはGoogle検索で著者情報を探すスペシャリストです。"
        "出力は原則日本語。質問が英語のときは英語で返答します。"
        "必ず根拠となるリンクを併記してください。"
    ),
    tools=[
        google_search
    ],
)


root_agent = LlmAgent(
    name="root_agent",
    model=MODEL,
    description=(
        "A multi-purpose research assistant agent. It can find academic papers, news, "
        "general information, and author information."
    ),
    # ※ ここも instruction（単数）
    instruction=(
        prompt.RESEARCH_AGENT_PROMPT
        + "\n\n出力規約: 日本語で簡潔に。必要に応じて箇条書きとリンクを提示。"
          "英語で質問された場合のみ英語で返答する。"
    ),
    tools=[
        find_papers_tool,
        find_news_tool,
        find_author_tool,
        find_author_details_tool,
        agent_tool.AgentTool(agent=google_search_agent),
    ],
)


settings = Settings()

agent = root_agent
# google-scholar/google_scholar/eval/test_vertex_eval.py

import pandas as pd
import vertexai
from vertexai.evaluation import EvalTask, PointwiseMetric, PointwiseMetricPromptTemplate
import os
import json
import asyncio
from typing import Dict, Any, List

from google.genai import types

import sys
import traceback 

script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from google_scholar.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


# --- Configuration ---
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(project_root, '.env')) 

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
EXPERIMENT_NAME = "google-scholar-adk-vertex-eval" 
EVAL_SET_PATH = os.path.join(script_dir, 'data', 'vertex.test.json') 

if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    print("Vertex AI initialized.")
else:
    print("Warning: GOOGLE_CLOUD_PROJECT environment variable not set. Vertex AI evaluation may not run correctly.")

def prepare_eval_dataset(file_path: str) -> pd.DataFrame:
    """
    Loads evaluation data from a JSON file. The JSON file is expected to be a dictionary
    where each value is a list (e.g., {"prompt": ["q1", "q2"], "reference": ["a1", "a2"]}).
    This format is directly suitable for pandas DataFrame creation.
    """
    print(f"DEBUG: Attempting to load dataset from: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read().strip()

            if not file_content:
                print(f"DEBUG: File '{file_path}' is empty.")
                return pd.DataFrame()

            try:
                print("DEBUG: Attempting to parse file as a dictionary of lists (Pandas DataFrame input format).")
                eval_data_dict = json.loads(file_content)
                
                if not isinstance(eval_data_dict, dict):
                    raise ValueError("JSON content is not a dictionary.")
                for key, value in eval_data_dict.items():
                    if not isinstance(value, list):
                        raise ValueError(f"Value for key '{key}' is not a list.")
                
                eval_df = pd.DataFrame(eval_data_dict)

                if 'eval_id' not in eval_df.columns:
                    eval_df['eval_id'] = [f"case_{i}" for i in range(len(eval_df))]
                if 'prompt' not in eval_df.columns:
                    eval_df['prompt'] = ['' for _ in range(len(eval_df))]
                if 'reference' not in eval_df.columns:
                    eval_df['reference'] = [None for _ in range(len(eval_df))]
                if 'reference_trajectory' not in eval_df.columns:
                    eval_df['reference_trajectory'] = [[] for _ in range(len(eval_df))]
                if 'user_query_original' not in eval_df.columns:
                    eval_df['user_query_original'] = eval_df['prompt'] 

                eval_df['predicted_trajectory'] = [[] for _ in range(len(eval_df))] 
                eval_df['full_agent_history_for_judge'] = ['' for _ in range(len(eval_df))]


                return eval_df

            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse JSON: {e}")
                print(f"DEBUG: Problematic content start: {file_content[:500]}...")
                print("Please ensure your 'vertex.test.json' is a valid JSON object formatted as a dictionary of lists.")
                return pd.DataFrame()
            except ValueError as e:
                print(f"ERROR: Invalid data structure for DataFrame: {e}")
                print("Please ensure your 'vertex.test.json' is a dictionary where each value is a list of equal length.")
                return pd.DataFrame()

    except FileNotFoundError:
        print(f"Error: Dataset file not found at {file_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred during dataset preparation: {e}")
        traceback.print_exc() 
        return pd.DataFrame()

# --- Custom Metrics Definitions (for LLM judging) ---
follows_trajectory_criteria: Dict[str, str] = {
    "follows_trajectory": """Evaluate whether the agent's final response logically follows from the sequence of actions (tool calls and results) it took.
    Consider these sub-points in your evaluation:
    - Does the response accurately reflect information gathered or actions performed during the trajectory?
    - Is the response consistent with the overall goal of the user's query and any constraints of the task?
    - Are there any illogical jumps or missing steps in reasoning when moving from the trajectory to the final response?"""
}

follows_trajectory_rating_rubric: Dict[str, str] = {
    "1": "The agent's response logically follows from its trajectory and reflects its actions/information gathered.",
    "0": "The agent's response does not logically follow from its trajectory or misrepresents its actions/information.",
}

response_follows_trajectory_prompt_template = PointwiseMetricPromptTemplate(
    criteria=follows_trajectory_criteria,
    rating_rubric=follows_trajectory_rating_rubric,
    input_variables=["prompt", "response", "predicted_trajectory", "user_query_original"],
)

response_follows_trajectory_metric = PointwiseMetric(
    metric="response_follows_trajectory",
    metric_prompt_template=response_follows_trajectory_prompt_template,
)

content_relevance_criteria: Dict[str, str] = {
    "content_relevance": """Evaluate if the agent provides information on research papers."""
}
content_relevance_rating_rubric: Dict[str, str] = {
    "1": "The response contains research papers about gluten",
    "0.5": "The response contains research papers about artificial intelligence, but not gluten",
    "0.25": "The response contains research papers unrelated to ai or gluten",
    "0": "The response does not contain any research papers",
   
}

content_relevance_prompt_template = PointwiseMetricPromptTemplate(
    criteria=content_relevance_criteria,
    rating_rubric=content_relevance_rating_rubric,
    input_variables=["prompt", "response"],
)

content_relevance_metric = PointwiseMetric(
    metric="content_relevance",
    metric_prompt_template=content_relevance_prompt_template,
)

# --- Main Evaluation Logic Function: run_vertex_evaluation ---
async def run_vertex_evaluation():
    """
    Orchestrates the Vertex AI evaluation process.
    It loads the dataset, runs the agent for each case, collects responses and trajectories,
    and then initiates the EvalTask.
    """
    if not PROJECT_ID:
        print("Skipping Vertex AI evaluation as GOOGLE_CLOUD_PROJECT is not set in .env.")
        return

    eval_dataset_df = prepare_eval_dataset(EVAL_SET_PATH)
    if eval_dataset_df.empty:
        print("No evaluation data loaded. Exiting.")
        return

    print(f"Loaded {len(eval_dataset_df)} evaluation cases for Vertex AI.")

    print("Generating agent responses and trajectories for evaluation...")

    APP_NAME_FOR_EVAL = "google_scholar_eval_app"
    USER_ID_FOR_EVAL = "eval_user"

    session_service = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name=APP_NAME_FOR_EVAL, session_service=session_service)

    temp_results_collection: List[Dict[str, Any]] = [] 

    for index, row in eval_dataset_df.iterrows():
        user_query = row["prompt"]
        eval_case_id = row["eval_id"]

        await session_service.create_session(
            app_name=APP_NAME_FOR_EVAL,
            user_id=USER_ID_FOR_EVAL,
            session_id=eval_case_id
        )

        content = types.Content(role="user", parts=[types.Part(text=user_query)])

        all_events_from_run = list(
            runner.run(
                user_id=USER_ID_FOR_EVAL,
                session_id=eval_case_id,
                new_message=content
            )
        )

        agent_response_text = "No response generated." 

        if all_events_from_run:
            for event in reversed(all_events_from_run):
                if hasattr(event, 'content') and event.content and hasattr(event.content, 'role') and event.content.parts:
                    if event.content.role == 'model':
                        is_text_response = all(p.function_call is None and p.function_response is None for p in event.content.parts)
                        text_part = next((p.text for p in event.content.parts if p.text), None)
                        
                        if is_text_response and text_part:
                            agent_response_text = text_part
                            break 

        formatted_predicted_trajectory_for_eval: List[Dict[str, Any]] = []
        judge_friendly_trajectory_data: List[Dict[str, Any]] = []

        for event in all_events_from_run:
            if not (hasattr(event, 'content') and event.content and event.content.parts):
                continue

            event_role = None
            if hasattr(event.content, 'role'):
                event_role = event.content.role

            for part in event.content.parts:
                if part.function_call:
                    tool_args = dict(part.function_call.args)
                    formatted_predicted_trajectory_for_eval.append({
                        "type": "tool_call",
                        "tool_name": part.function_call.name,
                        "tool_args": tool_args
                    })
                    judge_friendly_trajectory_data.append({
                        "type": "tool_call",
                        "tool_name": part.function_call.name,
                        "tool_args": tool_args
                    })
                elif part.function_response:
                    formatted_predicted_trajectory_for_eval.append({
                        "type": "tool_response",
                        "tool_name": part.function_response.name, 
                        "tool_output": part.function_response.response 
                    })
                    judge_friendly_trajectory_data.append({
                        "type": "tool_response",
                        "tool_name": part.function_response.name,
                        "tool_output_result": part.function_response.response
                    })
                elif part.text:
                    formatted_predicted_trajectory_for_eval.append({
                        "type": "text_message",
                        "role": event_role, 
                        "text": part.text
                    })
                    judge_friendly_trajectory_data.append({
                        "type": "text_message",
                        "role": event_role, 
                        "text": part.text
                    })
        
        judge_friendly_trajectory_string = json.dumps(judge_friendly_trajectory_data, indent=2)

        temp_results_collection.append({
            "index": index, 
            "response": agent_response_text,
            "predicted_trajectory": formatted_predicted_trajectory_for_eval, 
            "full_agent_history_for_judge": judge_friendly_trajectory_string,
        })

    for result in temp_results_collection:
        idx = result["index"] 
        eval_dataset_df.at[idx, "response"] = result["response"]
        eval_dataset_df.at[idx, "predicted_trajectory"] = result["predicted_trajectory"]
        eval_dataset_df.at[idx, "full_agent_history_for_judge"] = result["full_agent_history_for_judge"]

    print("Agent responses and trajectories generated.")

    metrics_to_run = [
        content_relevance_metric, 
        response_follows_trajectory_metric,
    ]

    eval_task = EvalTask(
        dataset=eval_dataset_df,
        metrics=metrics_to_run,
        experiment=EXPERIMENT_NAME, 
    )

    print("Running Vertex AI evaluation task...")
    eval_result = eval_task.evaluate()

    print("\n--- Detailed LLM-Judged Scores and Explanations ---")
    # Set pandas option to display all columns and wide format for console
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000) 
    
    # Explicitly select and print columns for both content relevance and trajectory for clarity
    print(eval_result.metrics_table[[
        'eval_id', 
        'prompt', 
        'response', 
        'content_relevance/score', 
        'response_follows_trajectory/score'
    ]])
    
    # Reset pandas option
    pd.reset_option('display.max_columns')
    pd.reset_option('display.width')

    print("\nDetailed results can be viewed in Vertex AI Experiments under experiment:", EXPERIMENT_NAME)


# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Starting Vertex AI Evaluation Process ---")
    try:
        if not (os.getenv("GOOGLE_API_KEY") or (os.getenv("GOOGLE_CLOUD_PROJECT") and os.getenv("GOOGLE_GENAI_USE_VERTEXAI") == "True")):
            print("Error: Required environment variables (GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT and GOOGLE_GENAI_USE_VERTEXAI='True') not set.")
            sys.exit(1)

        asyncio.run(run_vertex_evaluation())
        print("--- Vertex AI Evaluation Process Completed Successfully ---")

    except Exception as e:
        print(f"\n--- An error occurred during Vertex AI evaluation ---")
        print(f"Error details: {e}")
        traceback.print_exc() 
        sys.exit(1)

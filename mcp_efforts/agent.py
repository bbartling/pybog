import requests
import json
from typing import List, Dict, Any, Optional
import os
import google.generativeai as genai
from datetime import datetime

# --- Configuration ---
# Make sure your MCP server is running at this address.
MCP_SERVER_URL = "http://127.0.0.1:8000"

BOG_FILE_DESTINATION = "/mnt/c/Users/ben/Niagara4.11/JENEsys"
INSTRUCTIONS_PATH = "context/old/BACKUP_llm_bog_instructions.txt"

# Set up the Gemini API client.
# Ensure you have your GOOGLE_API_KEY set as an environment variable.
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
except ValueError as e:
    print(f"❌ Gemini API Error: {e}")
    gemini_model = None
# --- End Configuration ---


def _load_context_pack() -> str:
    try:
        with open(INSTRUCTIONS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def discover_tools() -> List[Dict[str, Any]]:
    """Fetches the list of available example tools from the MCP server."""
    print("🤖 Agent: Discovering available tools...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/examples")
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        tools = response.json()
        print(f"✅ Agent: Found {len(tools)} tools.")
        return tools
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Could not connect to MCP server at {MCP_SERVER_URL}.")
        print(f"   Is the server running? Error: {e}")
        return []


def get_api_documentation() -> Optional[str]:
    """Fetches the OpenAPI JSON docs from the MCP server for context."""
    print("\n🤖 Agent: Fetching API documentation (/openapi.json) for context...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/openapi.json")
        response.raise_for_status()
        docs = response.json()
        print("✅ Agent: Successfully fetched OpenAPI documentation.")
        return json.dumps(docs, indent=2)
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Could not fetch API documentation. Error: {e}")
        return None


def get_source_code_documentation() -> Optional[str]:
    """Fetches the source code introspection from the MCP server for deeper context."""
    print(
        "\n🤖 Agent: Fetching source code documentation (/source-code) for deeper analysis..."
    )
    try:
        response = requests.get(f"{MCP_SERVER_URL}/source-code")
        response.raise_for_status()
        docs = response.json()
        print("✅ Agent: Successfully fetched source code documentation.")
        return json.dumps(docs, indent=2)
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Could not fetch source code documentation. Error: {e}")
        return None


def select_best_tools(
    tools: List[Dict[str, Any]],
    goal: str,
    api_docs: str,
    log_steps: list,  # Pass the log list to record steps
    source_code_docs: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Selects the top 5 most appropriate tools by asking Gemini, using API docs and, if provided,
    source code introspection for enhanced context.
    """
    print(f"\n🤖 Agent: Analyzing tools to achieve goal: '{goal}'")
    log_steps.append(
        {
            "timestamp": datetime.now().isoformat(),
            "step": "Analyze Tools",
            "details": {"goal": goal},
        }
    )

    # This "soft" quality gate warns if descriptions are missing but doesn't stop the process.
    described_tools_count = sum(1 for tool in tools if tool.get("description"))
    if described_tools_count < 5:
        warning_msg = f"QUALITY GATE WARNING. Only {described_tools_count} of {len(tools)} examples have descriptions."
        print(f"⚠️  Agent: {warning_msg}")
        print(
            "   The LLM's initial choice may be less accurate. Proceeding with analysis..."
        )
        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Quality Gate",
                "details": {"level": "warning", "message": warning_msg},
            }
        )

    if not api_docs:
        error_msg = "API documentation is missing. Cannot continue."
        print(f"❌ Agent: {error_msg}")
        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Error",
                "details": {"message": error_msg},
            }
        )
        return []

    if not gemini_model:
        error_msg = "Gemini model is not configured. Cannot select a tool."
        print(f"❌ Agent: {error_msg}")
        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Error",
                "details": {"message": error_msg},
            }
        )
        return []

    # Provide a default description for tools that are missing one.
    simplified_tools = [
        {
            "name": tool["name"],
            "description": tool.get("description", "No description provided."),
        }
        for tool in tools
    ]

    # Construct the prompt for the LLM, including all available context.
    prompt = f"""
You are an expert controls engineer assistant. Your task is to select the best Python scripts (tools) to achieve a user's goal.
To make your decision, you must use the following sources of information.

---
CONTEXT 1: Main API Documentation (from /openapi.json)
{api_docs}
---
CONTEXT 2: Available Example Scripts (Tools)
{json.dumps(simplified_tools, indent=2)}
---
"""

    if source_code_docs:
        prompt += f"""
---
CONTEXT 3: Detailed Source Code Introspection of the Core 'builder' Module
This context provides a low-level view of the available classes, methods, and functions in the underlying library that the example scripts use. Use this to better understand the capabilities when the example descriptions are insufficient.
---
"""

    prompt += f"""
USER'S GOAL: "{goal}"

Analyze the user's goal. Cross-reference it with all the provided contexts. The API docs and example descriptions are your primary sources. Use the source code introspection (if provided) as a deeper reference to resolve ambiguity or to better understand the core functionalities being used.

Choose the top 5 best scripts from the list that will help the user achieve their goal. Rank them from most to least likely to succeed.

Respond with ONLY a JSON list of the 'name' of the best tools, like this:
["best_tool.py", "second_best_tool.py", "third_best_tool.py", "fourth_best_tool.py", "fifth_best_tool.py"]
"""

    log_steps.append(
        {
            "timestamp": datetime.now().isoformat(),
            "step": "LLM Consultation",
            "details": {"prompt_sent": prompt},
        }
    )

    try:
        if source_code_docs:
            print(
                "   -> Sending enhanced prompt to Gemini with API docs, examples, AND source code..."
            )
        else:
            print(
                "   -> Sending enhanced prompt to Gemini with API docs and examples..."
            )

        response = gemini_model.generate_content(prompt)
        # Clean up the response to make it valid JSON
        cleaned_response = response.text.strip().replace("'", '"')

        try:
            best_tool_names = json.loads(cleaned_response)
        except json.JSONDecodeError:
            print(
                f"❌ Agent: Gemini returned a response that could not be parsed as JSON: {response.text}"
            )
            return []

        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "LLM Response",
                "details": {"selected_tool_names": best_tool_names},
            }
        )

        if not best_tool_names:
            print("❌ Agent: Gemini returned an empty list of tools.")
            return []

        print(f"✅ Agent: Gemini selected top 5 tools: {best_tool_names}")

        # Find the full tool details from the names Gemini provided.

        # Create a dictionary for quick lookup
        tool_map = {tool["name"]: tool for tool in tools}

        # Reconstruct the list of tool objects in the order Gemini provided
        ordered_tools = [tool_map[name] for name in best_tool_names if name in tool_map]

        return ordered_tools

    except Exception as e:
        print(f"❌ Agent: An error occurred while calling the Gemini API: {e}")
        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Error",
                "details": {"source": "Gemini API", "message": str(e)},
            }
        )
        return []


def execute_tool(
    tool_name: str, output_dir: str, log_steps: list
) -> Optional[Dict[str, Any]]:
    """Sends a request to the MCP server to execute the specified tool."""
    print(f"\n🤖 Agent: Executing tool '{tool_name}'...")
    endpoint = f"{MCP_SERVER_URL}/examples/{tool_name}"
    payload = {"output_dir": output_dir}

    log_steps.append(
        {
            "timestamp": datetime.now().isoformat(),
            "step": "Execute Tool",
            "details": {
                "tool_name": tool_name,
                "endpoint": endpoint,
                "payload": payload,
            },
        }
    )

    print(
        f"   -> Sending POST request to: {endpoint} with payload: {json.dumps(payload)}"
    )
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        print("✅ Agent: Tool executed successfully!")
        return result
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to execute tool '{tool_name}'. Error: {e}"
        print(f"❌ Agent: {error_msg}")
        log_steps.append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Error",
                "details": {"source": "Tool Execution", "message": error_msg},
            }
        )
        if e.response:
            print(f"   Server response: {e.response.text}")
            log_steps[-1]["details"]["server_response"] = e.response.text
        return None


if __name__ == "__main__":
    # This is the user's goal that the agent will try to accomplish.
    user_goal = "create a bog file for a boiler and chiller central plant control logic to make heat if it is cold outside and cooling if it is hot outside and when economizer free cooling ranges are presetn between 50 and 60F nothing should be one. Cooling pump and chiller feed AHU cooling coils and heating pump and boiler feed AHU hot water coils. Logic needs adjustable setpoints for both starting and stopping both heat and cooling systems and hysterious on binary output command logic which enable heat or cool."

    # --- Set up logging ---
    run_timestamp = datetime.now()
    log_file_path = f"agent_log_{run_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    log_data = {
        "run_id": run_timestamp.isoformat(),
        "user_goal": user_goal,
        "steps": [],
    }

    try:
        # --- Main Logic Loop with Retry ---

        available_tools = discover_tools()
        log_data["steps"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "step": "Discover Tools",
                "details": {
                    "tool_count": len(available_tools),
                    "tools": available_tools,
                },
            }
        )

        api_docs = _load_context_pack()

        if not available_tools:
            print("\nExiting: Could not fetch required information from the server.")
        else:
            # 2. Make the first attempt to select a tool using only the API docs and tool list.
            print("\n--- Attempt 1: Using standard context ---")
            chosen_tools = select_best_tools(
                available_tools, user_goal, api_docs, log_steps=log_data["steps"]
            )

            # 3. If the first attempt fails, fetch the detailed source code and try again.
            if not chosen_tools:
                print("\n--- Attempt 2: Retrying with enhanced source code context ---")
                source_docs = get_source_code_documentation()
                log_data["steps"].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "step": "Fetch Source Code Docs",
                        "details": {"success": source_docs is not None},
                    }
                )

                if source_docs:
                    # This second call includes the powerful source_code_docs context.
                    chosen_tools = select_best_tools(
                        available_tools,
                        user_goal,
                        api_docs,
                        log_steps=log_data["steps"],
                        source_code_docs=source_docs,
                    )
                else:
                    print(
                        "❌ Agent: Could not fetch source code context for retry. Halting."
                    )

            # 4. If a tool was successfully chosen (on either attempt), execute it.
            if chosen_tools:
                # IMPORTANT: Make sure this path exists on your machine or change it.
                output_destination = BOG_FILE_DESTINATION

                execution_result = None
                for i, tool in enumerate(chosen_tools):
                    print(
                        f"\n--- Execution Attempt {i+1}/{len(chosen_tools)}: Trying tool '{tool['name']}' ---"
                    )
                    execution_result = execute_tool(
                        tool["name"],
                        output_dir=output_destination,
                        log_steps=log_data["steps"],
                    )
                    if execution_result:
                        print(
                            f"✅ Agent: Successfully executed '{tool['name']}'. Halting further attempts."
                        )
                        break  # Exit the loop on the first success

                if execution_result:
                    print("\n--- Final Execution Result ---")
                    print(json.dumps(execution_result, indent=2))
                    print("------------------------")
                    log_data["final_result"] = execution_result
                else:
                    print(
                        "\n❌ Agent: All selected tools failed to execute successfully."
                    )
                    log_data["final_result"] = {
                        "status": "failed",
                        "reason": "All selected tools failed.",
                    }

            else:
                print(
                    "\n❌ Agent: Could not select any suitable tools, even after a retry. Please review the user goal or the available tools."
                )
                log_data["final_result"] = {
                    "status": "failed",
                    "reason": "Could not select any suitable tools.",
                }

    finally:
        # --- Save the log file ---
        with open(log_file_path, "w") as f:
            json.dump(log_data, f, indent=2)
        print(f"\n✅ Detailed log saved to: {log_file_path}")

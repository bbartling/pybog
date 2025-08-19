# agent.py (Upgraded with API Doc context and quality gates)

import requests
import json
from typing import List, Dict, Any
import os
import google.generativeai as genai

# --- Configuration ---
MCP_SERVER_URL = "http://127.0.0.1:8000"
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
except ValueError as e:
    print(f"❌ Gemini API Error: {e}")
    gemini_model = None
# --- End Configuration ---

# CHANGED: Function to get API docs from the new endpoint
def get_api_documentation() -> str | None:
    """Fetches the BogFolderBuilder API documentation from the server."""
    print("\n🤖 Agent: Fetching API documentation for context...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/api-docs")
        response.raise_for_status()
        docs = response.json().get("documentation", "")
        print("✅ Agent: Successfully fetched API documentation.")
        return docs
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Could not fetch API documentation. Error: {e}")
        return None

def discover_tools() -> List[Dict[str, Any]]:
    # (This function is unchanged, logging was already good)
    print("🤖 Agent: Discovering available tools...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/examples")
        response.raise_for_status()
        tools = response.json()
        print(f"✅ Agent: Found {len(tools)} tools.")
        return tools
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Could not connect to MCP server at {MCP_SERVER_URL}.")
        print(f"   Is the server running? Error: {e}")
        return []

# CHANGED: This function is now much more powerful
def select_best_tool(tools: List[Dict[str, Any]], goal: str, api_docs: str) -> Dict[str, Any] | None:
    """
    Selects the most appropriate tool by asking Gemini, using API docs for context
    and checking a quality gate for tool descriptions.
    """
    print(f"\n🤖 Agent: Analyzing tools to achieve goal: '{goal}'")

    # NEW: Your "check 5 examples" quality gate
    described_tools_count = sum(1 for tool in tools if tool.get("description"))
    print(f"   -> Quality Check: Found {described_tools_count} tools with descriptions.")
    if described_tools_count < 5:
        print("   ⚠️  WARNING: Fewer than 5 tools have descriptions. The LLM's choice may be inaccurate.")
        # We can decide to continue or exit. For now, we'll continue with a warning.
    
    if not gemini_model:
        print("❌ Agent: Gemini model is not configured. Cannot select a tool.")
        return None

    simplified_tools = [{"name": tool["name"], "description": tool["description"]} for tool in tools]

    # NEW: The prompt is now much richer, including the API documentation as context
    prompt = f"""
    You are an expert controls engineer assistant. Your task is to select the best Python script (tool) to achieve a user's goal.
    To make your decision, you must use two sources of information: the main API documentation for the `BogFolderBuilder` library, and a list of available example scripts that use this library.

    ---
    CONTEXT 1: Main API Documentation
    {api_docs}
    ---
    CONTEXT 2: Available Example Scripts (Tools)
    {json.dumps(simplified_tools, indent=2)}
    ---
    
    USER'S GOAL: "{goal}"

    Analyze the user's goal. Cross-reference it with the methods available in the API documentation and the descriptions of the example scripts.
    Choose the single best script from the list that will help the user achieve their goal.
    
    Respond with ONLY the 'name' of the best tool and nothing else.
    
    BEST TOOL NAME:
    """

    try:
        print("   -> Sending enhanced prompt (with API docs) to Gemini...")
        response = gemini_model.generate_content(prompt)
        best_tool_name = response.text.strip()
        print(f"✅ Agent: Gemini selected tool: '{best_tool_name}'")

        for tool in tools:
            if tool['name'] == best_tool_name:
                return tool
        
        print(f"❌ Agent: Gemini suggested a tool ('{best_tool_name}') that doesn't exist.")
        return None
    except Exception as e:
        print(f"❌ Agent: An error occurred while calling the Gemini API: {e}")
        return None

def execute_tool(tool_name: str, output_dir: str) -> Dict[str, Any]:
    # (Function is the same, just the call to it will change)
    print(f"\n🤖 Agent: Executing tool '{tool_name}'...")
    endpoint = f"{MCP_SERVER_URL}/examples/{tool_name}"
    payload = {"output_dir": output_dir}
    print(f"   -> Sending POST request to: {endpoint} with payload: {json.dumps(payload)}")
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        result = response.json()
        print("✅ Agent: Tool executed successfully!")
        return result
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent: Failed to execute tool '{tool_name}'. Error: {e}")
        if e.response: print(f"   Server response: {e.response.text}")
        return {}

if __name__ == "__main__":
    user_goal = "create a bog file for a boiler and chiller central plant control logic to make heat if it is cold outside and cooling if it is hot outside and when economizer free cooling ranges are presetn between 50 and 60F nothing should be one. Cooling pump and chiller feed AHU cooling coils and heating pump and boiler feed AHU hot water coils. Logic needs adjustable setpoints for both starting and stopping both heat and cooling systems and hysterious on binary output command logic which enable heat or cool."

    # NEW: The main logic loop is updated
    api_docs = get_api_documentation()
    available_tools = discover_tools()
    
    if available_tools and api_docs:
        chosen_tool = select_best_tool(available_tools, user_goal, api_docs)

        if chosen_tool:
            # CHANGED: Using your specified output directory
            output_destination = r"C:\Users\ben\Documents\llm-bog-gen\bogs"
            execution_result = execute_tool(chosen_tool['name'], output_dir=output_destination)
            
            if execution_result:
                print("\n--- Execution Result ---")
                print(json.dumps(execution_result, indent=2))
                print("------------------------")
    else:
        print("\nExiting: Could not fetch required information from the server.")
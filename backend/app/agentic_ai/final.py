import os
import asyncio
import subprocess
import json
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any, Optional

# The user's other files indicate a package structure like `app.agentic_ai`.
# We'll use absolute imports from the `app` root for robustness.
from app.agentic_ai.extractor import ExtractorAgent
from app.agentic_ai.fitter import FitterAgent
from app.agentic_ai.model_client import Model_Client

# Load environment variables from a .env file, which should contain API keys and model names.
load_dotenv()

# We need a model client for the Extractor and Fitter agents.
# For consistency, we'll use the same configuration as the 'summarizer' agent
# in ThreeAgentTeam.py (key4, model4).
API_KEY = os.getenv("key4")
MODEL = os.getenv("model4")

class Autogen:
    """
    Orchestrates the AI-driven problem-solving pipeline.
    This class integrates agents for data extraction, solution generation,
    and final solution formatting.
    """
    def __init__(self, structure: str = ""):
        """
        Initializes the Autogen pipeline.

        This sets up the necessary LLM clients and instantiates the
        Extractor and Fitter agents. It will raise an error if the
        required environment variables for the API key and model are not set.
        """
        if not API_KEY or not MODEL:
            raise ValueError("API key 'key4' and model name 'model4' must be set in environment variables.")

        # Initialize a single LLM client to be shared by the extractor and fitter agents.
        llm_client = Model_Client(model=MODEL, API_KEY=API_KEY).getClient()

        self.extractor = ExtractorAgent(llm_client)
        
        # Pass the desired code structure to the FitterAgent.
        # An empty string tells the fitter to skip the refitting process.
        self.fitter = FitterAgent(llm_client, structure=structure)

    def _select_best_solution(self) -> Optional[Dict[str, Any]]:
        """
        Reads the final 'solutions.json' and selects the best solution.
        The priority is:
        1. The first "solved" solution.
        2. The first "Rescue_Team" solution if no "solved" ones exist.
        3. The first available solution as a last resort.
        """
        try:
            with open("solutions.json", 'r') as f:
                solutions = json.load(f)

            if not solutions or not isinstance(solutions, list):
                return None

            solved_solutions = [s for s in solutions if s.get("status") == "solved"]
            rescue_solutions = [s for s in solutions if s.get("team") == "Rescue_Team"]

            best_solution = None
            if solved_solutions:
                best_solution = solved_solutions[0]
            elif rescue_solutions:
                best_solution = rescue_solutions[0]
            else:
                best_solution = solutions[0]
            
            return best_solution

        except (FileNotFoundError, json.JSONDecodeError):
            return None


    async def run_pipeline(self, text: str, image_url: str = None, constraints: str = "", test_cases: str = ""):
        """
        Executes the full agentic pipeline asynchronously and returns the best solution.

        1.  Extracts structured problem data into `data.json`.
        2.  Runs the ThreeAgentTeam script to generate `solutions.json`.
        3.  Refits the code in `solutions.json` if a structure was provided.
        4.  Selects and returns the best solution from the final `solutions.json`.

        Returns:
            dict: A dictionary containing the best solution's data or an error message.
        """
        print("INFO: Starting Autogen pipeline...")

        # --- Step 1: Extraction ---
        print("INFO: Step 1: Running ExtractorAgent to process inputs...")
        full_text_prompt = f"Problem Statement: {text}\n\nConstraints: {constraints}\n\nTest Cases: {test_cases}"
        try:
            if image_url:
                await self.extractor.extract_image(image=image_url, user_text=full_text_prompt)
            else:
                await self.extractor.extract_text(text=full_text_prompt)
            print("INFO: Extractor finished. `data.json` created.")
        except Exception as e:
            print(f"ERROR: Step 1 (Extraction) failed: {e}")
            return {"error": "Extraction failed", "details": str(e)}

        # --- Step 2: Solution Generation (ThreeAgentTeam) ---
        print("INFO: Step 2: Running ThreeAgentTeam to generate solutions...")
        try:
            project_root = Path(__file__).resolve().parent.parent.parent
            module_path = "app.agentic_ai.ThreeAgentTeam"
            process = subprocess.run(
                ['python', '-m', module_path],
                capture_output=True,
                text=True,
                check=True,
                timeout=600,
                cwd=project_root
            )
            print("INFO: ThreeAgentTeam finished. `solutions.json` created.")

        except FileNotFoundError as e:
            print(f"ERROR: Step 2 (ThreeAgentTeam) failed: {e}")
            return {"error": "Script not found", "details": str(e)}
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Step 2 (ThreeAgentTeam) script exited with an error.")
            print(f"Stderr: {e.stderr}")
            return {"error": "Solution generation failed", "details": e.stderr}
        except subprocess.TimeoutExpired as e:
            print(f"ERROR: Step 2 (ThreeAgentTeam) timed out after 10 minutes.")
            return {"error": "Solution generation timed out", "details": str(e)}

        # --- Step 3: Fitting ---
        print("INFO: Step 3: Running FitterAgent to refactor code in solutions.json...")
        try:
            if not self.fitter.fit_solutions_in_file():
                 print("ERROR: Step 3 (Fitter) failed during file operations.")
                 return {"error": "Fitter failed", "details": "Could not read or write solutions.json"}
            print("INFO: Fitter finished successfully.")
        except Exception as e:
            print(f"ERROR: Step 3 (Fitter) failed with an unexpected error: {e}")
            return {"error": "Fitter failed", "details": str(e)}

        # --- Step 4: Select and Format Best Solution ---
        print("INFO: Step 4: Selecting best solution from solutions.json...")
        best_solution = self._select_best_solution()

        if not best_solution:
            return {"error": "No valid solution found", "details": "solutions.json was empty or invalid after the pipeline ran."}
        
        # Map the keys from the solution to the format expected by the backend (__init__.py)
        return {
            "approach": best_solution.get("summary"),
            "time_complexity": best_solution.get("time_complexity"),
            "space_complexity": best_solution.get("space_complexity"),
            "code": best_solution.get("code")
        }


def main(text: str, image_url: str = None, constraints: str = "", test_cases: str = "", structure: str = "") -> dict:
    """
    A synchronous wrapper to initialize and run the Autogen pipeline.

    Args:
        structure (str): The code structure to enforce. If empty, fitting is skipped.
        See Autogen.run_pipeline for other argument details.

    Returns:
        dict: The final solution dictionary or an error dictionary.
    """
    try:
        pipeline = Autogen(structure=structure)
        result = asyncio.run(pipeline.run_pipeline(text, image_url, constraints, test_cases))
        return result
    except Exception as e:
        print(f"FATAL: An unexpected error occurred in the main pipeline runner: {e}")
        return {"error": "A fatal error occurred in the pipeline", "details": str(e)}

# This block allows the script to be tested directly from the command line.
if __name__ == '__main__':
    print("--- Running final.py in standalone test mode ---")
    sample_problem_text = "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`."
    sample_constraints = "You may assume that each input would have exactly one solution, and you may not use the same element twice."
    sample_test_cases = json.dumps([{"input": {"nums": [2, 7, 11, 15], "target": 9}, "expected": [0, 1]}])
    sample_structure = """
class Solution {
    public int[] twoSum(int[] nums, int target) {
        // Your code here
    }
}
"""
    final_status = main(
        text=sample_problem_text,
        constraints=sample_constraints,
        test_cases=sample_test_cases,
        structure=sample_structure
    )

    print("\n--- Final Pipeline Status ---")
    print(json.dumps(final_status, indent=4))


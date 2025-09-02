import json
from autogen_agentchat.agents import AssistantAgent
from typing import Dict, Any

class FitterAgent():
    def __init__(self, llm, structure: str):
        self.fitter = AssistantAgent(
            name="Fitter",
            description="Role is to adjust code according to user needs.",
            model_client=llm,
            system_message=f"""You are an expert in formatting and adjusting code within function blocks. Your task is to adjust the given code to fit the following structure exactly: {structure if structure.strip() else 'the same structure as provided'}. Finally, you must analyze the provided code to determine its approach, time complexity, and **space complexity**.

The output must be a single JSON object with four keys:
1.  "code": The adjusted code block as a string.
2.  "approach": A string describing the algorithm or method used.
3.  "time_complexity": A string representing the time complexity (e.g., "O(n^2)").
4.  "space_complexity": A string representing the space complexity (e.g., "O(1)").

If any of these cannot be determined, provide a descriptive string like "N/A" or "Not applicable." Ensure the output is a valid JSON object without any additional text or formatting.
"""
        )
        self.structure = structure

    def _analyze_code(self, code: str) -> Dict[str, str]:
        """
        Analyzes a code snippet and returns its approach, time, and space complexity.
        Includes robust error handling for JSON parsing.
        """
        try:
            task = f"Adjust this code to fit the structure '{self.structure}' and analyze it:\n\n{code}"
            response_str = self.fitter.run(task=task)
            
            analysis = json.loads(response_str)
            
            if not all(k in analysis for k in ["code", "approach", "time_complexity", "space_complexity"]):
                raise ValueError("JSON response is missing required keys.")
            
            return analysis
        
        except json.JSONDecodeError:
            print(f"Error: Failed to parse JSON from agent response. Response was:\n{response_str}")
            return {"code": code, "approach": "Parsing error", "time_complexity": "Parsing error", "space_complexity": "Parsing error"}
        except ValueError as e:
            print(f"Error: {e}. Response was:\n{response_str}")
            return {"code": code, "approach": "Invalid response format", "time_complexity": "Invalid response format", "space_complexity": "Invalid response format"}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return {"code": code, "approach": "Unknown error", "time_complexity": "Unknown error", "space_complexity": "Unknown error"}

    def fit(self, code_to_fit: str) -> Dict[str, str]:
        """
        Finds the best solution from a file, analyzes it, and returns the
        adjusted code with its analysis, now including space complexity.
        """
        try:
            with open("solutions.json", 'r') as f:
                solutions = json.load(f)
        except FileNotFoundError:
            print("Error: 'solutions.json' file not found.")
            return {"code": "", "approach": "No suitable solution found", "time_complexity": "N/A", "space_complexity": "N/A"}
        except json.JSONDecodeError:
            print("Error: 'solutions.json' is not a valid JSON file.")
            return {"code": "", "approach": "JSON file parsing error", "time_complexity": "N/A", "space_complexity": "N/A"}

        solved_solutions = [s for s in solutions if s.get("status") == "solved"]
        rescue_solutions = [s for s in solutions if s.get("team") == "Rescue_Team"]
        
        best_solution = None
        if solved_solutions:
            best_solution = solved_solutions[0]
        elif rescue_solutions:
            best_solution = rescue_solutions[0]
        
        if best_solution is None:
            return {
                "code": "",
                "approach": "No suitable solution found",
                "time_complexity": "N/A",
                "space_complexity": "N/A"
            }
        
        code = best_solution.get("code", "")
        if not code:
            return {
                "code": "",
                "approach": "Selected solution has no code",
                "time_complexity": "N/A",
                "space_complexity": "N/A"
            }

        analysis = self._analyze_code(code)
        
        return {
            "code": analysis.get("code", ""),
            "approach": analysis.get("approach", "N/A"),
            "time_complexity": analysis.get("time_complexity", "N/A"),
            "space_complexity": analysis.get("space_complexity", "N/A")
        }
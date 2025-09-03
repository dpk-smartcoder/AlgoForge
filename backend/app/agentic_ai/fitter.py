import json
from autogen_agentchat.agents import AssistantAgent
from typing import Dict, Any, List
import re

class FitterAgent():
    def __init__(self, llm, structure: str):
        self.structure = structure.strip()
        # The system message is updated to focus ONLY on refactoring code.
        self.fitter = AssistantAgent(
            name="Fitter",
            description="Role is to adjust code according to a user-provided structure.",
            model_client=llm,
            system_message=f"""You are an expert in refactoring Python code. Your task is to take a given code snippet and place it inside the following structure without altering the core logic.

Structure to use:
{self.structure}

Respond ONLY with a single valid JSON object containing one key, "code", where the value is the refactored code as a string. Do not include any other text, explanations, or markdown.
"""
        )

    def _refit_code(self, code: str) -> str:
        """
        Uses the LLM to refit a single code snippet into the required structure.
        """
        if not self.structure:
            return code # Return original code if no structure is defined.

        try:
            # The task prompt is now simpler, focusing only on the code refitting.
            task = f"Refit the following code into the predefined structure:\n\n{code}"
            
            response_obj = self.fitter.run(task=task)
            
            # Extract the string content from the response
            if hasattr(response_obj, 'messages') and response_obj.messages:
                response_str = response_obj.messages[-1].content
            else:
                response_str = str(response_obj)

            # Use regex to find the JSON object within the response string
            match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if not match:
                print(f"Error: Could not find a JSON object in the LLM response. Response was:\n{response_str}")
                return code # Return original code on failure

            analysis = json.loads(match.group(0))
            
            return analysis.get("code", code) # Return original code if key is missing

        except json.JSONDecodeError:
            print(f"Error: Failed to parse JSON from agent response. Response was:\n{response_str}")
            return code # Return original code on failure
        except Exception as e:
            print(f"An unexpected error occurred during refitting: {e}")
            return code # Return original code on failure

    def fit_solutions_in_file(self) -> bool:
        """
        Reads 'solutions.json', refits the code for every solution if a structure is defined,
        and then saves the updated data back to 'solutions.json'.
        If no structure is provided, it does nothing.
        Returns True on success, False on failure.
        """
        # If no structure is provided, the process is trivially successful.
        if not self.structure:
            print("INFO: No structure provided to FitterAgent. Skipping refitting.")
            return True

        try:
            with open("solutions.json", 'r') as f:
                solutions = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error: Cannot process solutions.json for fitting. Reason: {e}")
            return False

        fitted_solutions = []
        for solution in solutions:
            original_code = solution.get("code", "")
            
            # Only refit if there is code to process
            if original_code:
                print(f"INFO: Refitting code for team: {solution.get('team', 'Unknown')}")
                fitted_code = self._refit_code(original_code)
            else:
                fitted_code = ""

            # Preserve all original data, only updating the code
            solution['code'] = fitted_code
            fitted_solutions.append(solution)
        
        try:
            # Write the updated list of solutions back to the same file
            with open("solutions.json", 'w') as f:
                json.dump(fitted_solutions, f, indent=4)
            print("INFO: Successfully refitted solutions and updated solutions.json.")
            return True
        except IOError as e:
            print(f"Error: Could not write updated solutions to solutions.json. Reason: {e}")
            return False


from autogen_agentchat.agents import AssistantAgent
from typing import List, Dict
from dotenv import load_dotenv
import os
import json # Make sure to import the json library at the top of your file
load_dotenv()
prompt=os.getenv("Start_prompt")
class AlgoForgeAgent:
    def __init__(self, name: str, llm_client, executor):
        self.name = name
        self.llm = AssistantAgent(
            name=f"{name}_LLM",
            description=f"Code generator for {name}",
            model_client=llm_client,
            system_message=prompt
        )
        self.executor = executor
        self.history = []

    async def generate_code(self, problem_prompt: str) -> str:
        """Ask LLM to generate code and extract it from the JSON response."""
        result = await self.llm.run(task=problem_prompt)
        llm_response_str = result.messages[-1]["content"]

        try:
            # 1. Parse the JSON string into a Python dictionary
            response_data = json.loads(llm_response_str)

            # 2. Extract the executable code using the "code" key
            executable_code = response_data["code"]

            # 3. Store the clean code in history
            self.history.append({"code": executable_code, "result": None})

            # 4. Return only the executable code
            return executable_code

        except (json.JSONDecodeError, KeyError) as e:
            # Handle cases where the LLM returns malformed JSON or doesn't include the "code" key
            print(f"Error parsing LLM response: {e}")
            print(f"Malformed response: {llm_response_str}")
            # Store the malformed response for debugging
            self.history.append({"code": f"Parsing Error: {llm_response_str}", "result": None})
            # Return an empty string or handle the error as appropriate
            return ""

    async def run_tests(self, code: str, test_cases: List[Dict]) -> Dict:
        """Run generated code on test cases."""
        result = await self.executor.run_code(code, test_cases)
        self.history[-1]["result"] = result
        return result

    async def refine_code_withoutCotext(self,problem_prompt: str, last_code: str) -> str:
        """Re-prompt LLM with previous code with new State."""
        self.llm.reset()
        refine_prompt = (
            f"Here is the problem consisiting of problem , constraints and test cases:\n{problem_prompt}\n\n"
            f"Here is the logic , approach  and code of the problem i thought and build on my behalf use it if it can help you for getting the correct , accurate and optimal code of the problem :\n{last_code}\n\n"
            + os.getenv('Last_prompt')
        )
        return await self.generate_code(refine_prompt)
    
    async def refine_code_withContext(self,problem_prompt:str,last_code:str,fail_logs:str)->str:
        """Refining the code after the code executor Permission"""
        refine_prompt = (
            f"Here is the problem consisiting of problem , constraints and test cases:\n{problem_prompt}\n\n"
            f"Here is the logic and code of the problem i thought on my behalf use it for getting the correct , accurate and optimal code of the problem :\n{last_code}\n\n"
            f"Here are the corners where it fails to get conquer the problem :\n{fail_logs}\n\n"
            + os.getenv('Last_prompt')
        )
        return await self.generate_code(refine_prompt)
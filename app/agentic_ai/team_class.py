from autogen_agentchat.agents import AssistantAgent
from autogen_core import CancellationToken
from typing import List, Dict
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()
cancellation_token = CancellationToken()

class AlgoForgeAgent:
    def __init__(self, name: str, llm_client, executor, language: str):
        self.name = name
        self.executor = executor
        self.language = language.lower()
        self.base_prompt = os.getenv("Start_prompt", "").replace("{language}", self.language)

        self.llm = AssistantAgent(
            name=f"{name}_LLM",
            description=f"Code generator for {name} in {self.language}",
            model_client=llm_client,
            system_message=self.base_prompt
        )
        self.history = []

    async def generate_code(self, problem_prompt: str) -> str:
        """
        Ask LLM to generate code in the specified language.
        Returns the code string.
        """
        import ast

        def clean_json_str(s: str) -> str:
            s = s.replace('\u00A0', ' ')
            # Remove trailing commas before closing braces/brackets
            s = re.sub(r',(\s*[}\]])', r'\1', s)
            # Escape unescaped newlines in "code" field (inside double quotes)
            def _escape_code_newlines(m):
                code_val = m.group(2)
                # Replace unescaped newlines with \\n
                code_val_escaped = code_val.replace('\n', '\\n')
                return m.group(1) + code_val_escaped + '"'
            s = re.sub(r'("code"\s*:\s*")((?:[^"\\]|\\.)*?)"', _escape_code_newlines, s, flags=re.DOTALL)
            return s

        result = await self.llm.run(task=problem_prompt)
        llm_response_str = result.messages[-1].content
        executable_code = ""

        # --- NEW, MORE ROBUST PARSING LOGIC ---

        # 1. Try to find and extract content from a ```json ... ``` block.
        json_match = re.search(r'```json\s*(.*?)\s*```', llm_response_str, re.DOTALL)

        string_to_parse = llm_response_str
        if json_match:
            string_to_parse = json_match.group(1)
        else:
            # Try to find the largest {...} block in the string
            brace_match = re.search(r'\{[\s\S]*\}', llm_response_str)
            if brace_match:
                string_to_parse = brace_match.group(0)

        # 2. Attempt to parse JSON.
        try:
            cleaned_str = clean_json_str(string_to_parse)
            response_data = json.loads(cleaned_str)
        except (json.JSONDecodeError, KeyError):
            # Try cleaning further and reattempt
            try:
                cleaned_str = clean_json_str(string_to_parse)
                response_data = json.loads(cleaned_str)
            except (json.JSONDecodeError, KeyError):
                # Try ast.literal_eval with JS -> Python conversion
                try:
                    temp_str = string_to_parse.replace("null", "None").replace("true", "True").replace("false", "False")
                    response_data = ast.literal_eval(temp_str)
                except Exception:
                    # Fallback to language-specific code block
                    print("Could not parse JSON. Trying to extract from a language-specific markdown block as a fallback.")
                    pattern = rf'```{self.language}\s*(.*?)\s*```'
                    code_match = re.search(pattern, llm_response_str, re.DOTALL | re.IGNORECASE)
                    if code_match:
                        executable_code = code_match.group(1).strip()
                        print(f"Successfully extracted {self.language} code from markdown fallback.")
                    else:
                        print(f"ERROR: All parsing methods failed. Could not find valid JSON or a '{self.language}' code block.")
                        print(f"Malformed response: {llm_response_str}")
                        self.history.append({"code": f"Parsing Error: {llm_response_str}", "result": None, "language": self.language})
                        return ""
                else:
                    executable_code = response_data.get("code", "")
                    if not executable_code:
                        print("WARNING: Parsed JSON missing 'code' field.")
                    self.history.append({"code": executable_code, "result": None, "language": self.language})
                    return executable_code
        else:
            # Optional: Check if the LLM followed language instructions.
            response_language = response_data.get("language", "").lower()
            if response_language and response_language != self.language:
                print(f"WARNING: LLM disobeyed instructions. Requested {self.language}, but it provided {response_language}.")
            executable_code = response_data.get("code", "")
            if not executable_code:
                print("WARNING: Parsed JSON missing 'code' field.")

        self.history.append({"code": executable_code, "result": None, "language": self.language})
        return executable_code

    async def run_tests(self, code: str, test_cases: List[Dict]) -> Dict:
        """
        Runs code against test cases and collects all results.
        NOTE: This is now compatible with the async generator in the executor.
        """
        all_results = []
        # The executor's run_code is now an async generator, so we iterate through it.
        async for result in self.executor.run_code(code, test_cases):
            all_results.append(result)

        # Store the full list of results.
        if self.history:
            self.history[-1]["result"] = all_results
        
        # For compatibility, you might summarize the result, e.g., by checking if all passed.
        all_passed = all(r.get("passed", False) for r in all_results)
        summary = {
            "all_passed": all_passed,
            "results": all_results
        }
        return summary

    async def refine_code_withoutCotext(self, problem_prompt: str, last_code: str) -> str:
        """Re-prompt LLM with previous code."""
        await self.llm.on_reset(cancellation_token)
        refine_prompt = (
            self.base_prompt+
            f"Here is the problem consisting of problem, constraints, and test cases:\n{problem_prompt}\n\n"
            f"Here is the code I previously attempted for the problem in {self.language}:\n{last_code}\n\n"
            + os.getenv('Last_prompt')
        )
        return await self.generate_code(refine_prompt)
    
    async def refine_code_withContext(self, last_code: str, fail_logs: str) -> str:
        """Refine code using feedback from failed tests."""
        refine_prompt = (
            f"My previous code attempt in {self.language} failed some tests. Here is the code:\n{last_code}\n\n"
            f"Here are the test cases it failed:\n{fail_logs}\n\n"
            + os.getenv('Last_prompt')
        )
        return await self.generate_code(refine_prompt)


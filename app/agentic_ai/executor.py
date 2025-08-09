import subprocess
import tempfile
import json
import os
import asyncio
import hashlib
import sys

class CodeExecutor:
    def __init__(self, language="python"):
        self.language = language.lower()
        self.last_code_hash = None
        self.compiled_path = None
        self.last_results = []
        self.temp_dir_obj = None # Store the TemporaryDirectory object
        self.class_name = "Main"

    def _hash_code(self, code: str):
        return hashlib.sha256(code.encode()).hexdigest()

    def _cleanup_temp(self):
        """Safely cleans up the temporary directory."""
        if self.temp_dir_obj:
            try:
                self.temp_dir_obj.cleanup()
            except Exception as e:
                # Log errors if cleanup fails, but don't crash
                print(f"Error cleaning up temp directory: {e}", file=sys.stderr)
        self.temp_dir_obj = None
        self.compiled_path = None


    async def run_code(self, code: str, test_cases: list, mode="run_all"):
        results = []
        code_hash = self._hash_code(code)

        if mode == "reset":
            self.last_code_hash = None
            self.last_results = []
            self._cleanup_temp()
            return {"results": [], "all_passed": True, "status": "reset"}

        # Determine which test cases to run
        if mode == "run_failed":
            # Filter for failed or error cases from the last run
            test_cases_to_run = [
                r for r in self.last_results if not r.get("passed", False)
            ]
            # Re-map to original test case format
            test_cases_to_run = [
                {"input": r["input"], "expected": r["expected"]} for r in test_cases_to_run
            ]
            if not test_cases_to_run:
                return {"results": self.last_results, "all_passed": True, "status": "no_failed_tests"}
        else:
            test_cases_to_run = test_cases

        # --- Language-specific execution logic ---
        # This part remains largely the same, but with improved temp dir management

        # PYTHON
        if self.language == "python":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                # For python, the "compiled_path" is the script file path
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(code)
                    self.compiled_path = f.name
                self.last_code_hash = code_hash

            if mode == "compile_only":
                return {"results": [], "all_passed": True, "status": "compiled"}

            for case in test_cases_to_run:
                try:
                    process = await asyncio.create_subprocess_exec(
                        "python3", self.compiled_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(input=json.dumps(case["input"]).encode()), timeout=2)
                    output = stdout.decode().strip()
                    if stderr:
                        result = {"input": case["input"], "error": stderr.decode().strip(), "passed": False}
                    else:
                        passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    process.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                results.append(result)
                yield result

        # JAVA
        elif self.language == "java":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                self.temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = self.temp_dir_obj.name

                self.class_name = "Main" # Reset class name
                for line in code.splitlines():
                    if "public class " in line:
                        self.class_name = line.split("public class ")[1].split("{")[0].strip()
                        break

                java_path = os.path.join(tmpdir, f"{self.class_name}.java")
                with open(java_path, "w") as f: f.write(code)

                compile_proc = await asyncio.create_subprocess_exec("javac", java_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                _, stderr = await compile_proc.communicate()

                if compile_proc.returncode != 0:
                    error_msg = stderr.decode().strip()
                    for case in test_cases_to_run:
                        yield {"input": case["input"], "error": f"Compilation error: {error_msg}", "passed": False}
                    return

                self.compiled_path = tmpdir
                self.last_code_hash = code_hash

            if mode == "compile_only":
                return {"results": [], "all_passed": True, "status": "compiled"}

            for case in test_cases_to_run:
                try:
                    run_proc = await asyncio.create_subprocess_exec(
                        "java", "-cp", self.compiled_path, self.class_name,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(input=json.dumps(case["input"]).encode()), timeout=2)
                    output = stdout.decode().strip()
                    if stderr:
                         result = {"input": case["input"], "error": stderr.decode().strip(), "passed": False}
                    else:
                        passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    run_proc.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                results.append(result)
                yield result

        # CPP
        elif self.language == "cpp":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                self.temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = self.temp_dir_obj.name
                cpp_path = os.path.join(tmpdir, "solution.cpp")
                exe_path = os.path.join(tmpdir, "solution.out")

                with open(cpp_path, "w") as f: f.write(code)

                compile_proc = await asyncio.create_subprocess_exec("g++", cpp_path, "-o", exe_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                _, stderr = await compile_proc.communicate()

                if compile_proc.returncode != 0:
                    error_msg = stderr.decode().strip()
                    for case in test_cases_to_run:
                        yield {"input": case["input"], "error": f"Compilation error: {error_msg}", "passed": False}
                    return

                self.compiled_path = exe_path
                self.last_code_hash = code_hash

            if mode == "compile_only":
                return {"results": [], "all_passed": True, "status": "compiled"}

            for case in test_cases_to_run:
                try:
                    run_proc = await asyncio.create_subprocess_exec(
                        self.compiled_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(input=json.dumps(case["input"]).encode()), timeout=2)
                    output = stdout.decode().strip()
                    if stderr:
                        result = {"input": case["input"], "error": stderr.decode().strip(), "passed": False}
                    else:
                        passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    run_proc.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                results.append(result)
                yield result

        self.last_results = results

async def main():
    """
    Main loop to read commands from stdin and write results to stdout.
    """
    # Initialize one executor for each language
    executors = {
        "python": CodeExecutor(language="python"),
        "java": CodeExecutor(language="java"),
        "cpp": CodeExecutor(language="cpp"),
    }

    # Use a stream reader to handle stdin asynchronously
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break # End of input

        try:
            command = json.loads(line)
            language = command.get("language")
            if language not in executors:
                response = {"error": f"Unsupported language: {language}", "passed": False}
                print(json.dumps(response), flush=True)
                continue

            executor = executors[language]
            code = command.get("code", "")
            test_cases = command.get("test_cases", [])
            mode = command.get("mode", "run_all")

            # Get the async generator
            runner = executor.run_code(code, test_cases, mode=mode)

            # Await and process results
            async for result in runner:
                print(json.dumps(result), flush=True)

        except json.JSONDecodeError:
            response = {"error": "Invalid JSON command", "passed": False}
            print(json.dumps(response), flush=True)
        except Exception as e:
            response = {"error": f"An unexpected error occurred: {str(e)}", "passed": False}
            print(json.dumps(response), flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

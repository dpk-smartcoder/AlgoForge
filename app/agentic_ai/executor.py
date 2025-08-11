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
            # FIX: Changed `return` to `yield`
            yield {"results": [], "all_passed": True, "status": "reset"}
            return # Exit the generator after yielding

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
                yield {"results": self.last_results, "all_passed": True, "status": "no_failed_tests"}
                return # Exit the generator

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
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return # Exit the generator

            # Determine temp dir and filename for mounting and inside container path
            temp_dir = os.path.dirname(self.compiled_path)
            filename = os.path.basename(self.compiled_path)
            container_path = f"/workspace/{filename}"

            for case in test_cases_to_run:
                try:
                    if isinstance(case["input"], str):
                        input_data = case["input"].encode()
                    elif isinstance(case["input"], (list, tuple)):
                        input_data = " ".join(map(str, case["input"])).encode()
                    else:
                        input_data = json.dumps(case["input"]).encode()

                    process = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{temp_dir}:/workspace",
                        "dsa-executor-image",
                        "python3", container_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(input=input_data), timeout=2)
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
            # For Java, for each test case, generate a temp directory and a wrapper Main class with hardcoded arrays.
            # Extract imports and user code body once, reuse for each test case.
            code_lines = code.splitlines()
            import_lines = []
            user_code_body = []
            found_non_import = False
            for line in code_lines:
                striped = line.strip()
                if not found_non_import and (striped.startswith("import ") or striped.startswith("package ")):
                    import_lines.append(line)
                else:
                    found_non_import = True
                    user_code_body.append(line)
            # Remove any import statements from user code body (just in case)
            user_code_body = [l for l in user_code_body if not l.strip().startswith("import ")]
            # Ensure "import java.util.*;" is present
            has_java_util = any("import java.util.*;" in l for l in import_lines)
            if not has_java_util:
                import_lines.append("import java.util.*;")

            if mode == "compile_only":
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return # Exit the generator

            for case in test_cases_to_run:
                # For each test case, create its own temp directory and wrapper
                temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = temp_dir_obj.name
                # Extract value and limit arrays from input
                case_input = case["input"]
                value_arr = []
                limit_arr = []
                try:
                    if isinstance(case_input, dict) and "value" in case_input and "limit" in case_input:
                        value_arr = case_input["value"]
                        limit_arr = case_input["limit"]
                    else:
                        raise Exception("Input format error: expected dict with 'value' and 'limit' keys")
                except Exception as e:
                    temp_dir_obj.cleanup()
                    yield {"input": case["input"], "error": f"Input extraction error: {str(e)}", "passed": False}
                    continue
                # Convert arrays to Java array syntax
                def to_java_array(arr):
                    return "{" + ", ".join(str(x) for x in arr) + "}"
                value_str = to_java_array(value_arr)
                limit_str = to_java_array(limit_arr)
                n_val = len(value_arr)
                # Build wrapper Main class
                wrapper_code = (
                    "public class Main {\n"
                    "    public static void main(String[] args) {\n"
                    f"        int n = {n_val};\n"
                    f"        int[] value = {value_str};\n"
                    f"        int[] limit = {limit_str};\n"
                    "        Solution sol = new Solution();\n"
                    "        System.out.println(sol.maximumActivationValue(value, limit));\n"
                    "    }\n"
                    "}\n"
                )
                # Assemble: imports, wrapper, user code body
                full_code = "\n".join(import_lines) + "\n\n" + wrapper_code + "\n" + "\n".join(user_code_body)
                java_path = os.path.join(tmpdir, "Main.java")
                with open(java_path, "w") as f:
                    f.write(full_code)
                # Compile inside docker
                try:
                    compile_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{tmpdir}:/workspace",
                        "dsa-executor-image",
                        "javac", "/workspace/Main.java",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await compile_proc.communicate()
                    if compile_proc.returncode != 0:
                        error_msg = stderr.decode().strip()
                        temp_dir_obj.cleanup()
                        yield {"input": case["input"], "error": f"Compilation error: {error_msg}", "passed": False}
                        continue
                except Exception as e:
                    temp_dir_obj.cleanup()
                    yield {"input": case["input"], "error": f"Compilation exception: {str(e)}", "passed": False}
                    continue
                # Run the compiled Main class (no stdin)
                try:
                    run_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{tmpdir}:/workspace",
                        "dsa-executor-image",
                        "java", "-cp", "/workspace", "Main",
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(input=None), timeout=2)
                    output = stdout.decode().strip()
                    if stderr and stderr.decode().strip():
                        result = {"input": case["input"], "error": stderr.decode().strip(), "passed": False}
                    else:
                        passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    run_proc.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                except Exception as e:
                    result = {"input": case["input"], "error": f"Runtime exception: {str(e)}", "passed": False}
                results.append(result)
                yield result
                temp_dir_obj.cleanup()

        # CPP
        elif self.language == "cpp":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                self.temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = self.temp_dir_obj.name
                cpp_path = os.path.join(tmpdir, "solution.cpp")
                exe_path = os.path.join(tmpdir, "solution.out")

                with open(cpp_path, "w") as f: f.write(code)

                # Compile inside docker
                compile_proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm", "-i",
                    "-v", f"{tmpdir}:/workspace",
                    "dsa-executor-image",
                    "g++", "/workspace/solution.cpp", "-o", "/workspace/solution.out",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await compile_proc.communicate()

                if compile_proc.returncode != 0:
                    error_msg = stderr.decode().strip()
                    for case in test_cases_to_run:
                        yield {"input": case["input"], "error": f"Compilation error: {error_msg}", "passed": False}
                    return

                self.compiled_path = exe_path
                self.last_code_hash = code_hash

            if mode == "compile_only":
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return # Exit the generator

            temp_dir = os.path.dirname(self.compiled_path)
            exe_filename = os.path.basename(self.compiled_path)
            container_path = f"/workspace/{exe_filename}"

            for case in test_cases_to_run:
                try:
                    if isinstance(case["input"], str):
                        input_data = case["input"].encode()
                    elif isinstance(case["input"], (list, tuple)):
                        input_data = " ".join(map(str, case["input"])).encode()
                    else:
                        input_data = json.dumps(case["input"]).encode()

                    run_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{temp_dir}:/workspace",
                        "dsa-executor-image",
                        container_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(input=input_data), timeout=2)
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

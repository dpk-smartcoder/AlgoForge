import subprocess
import tempfile
import json
import os
import asyncio
import hashlib
import sys
import re

class CodeExecutor:
    def __init__(self, language="python"):
        self.language = language.lower()
        self.last_code_hash = None
        self.compiled_path = None
        self.last_results = []
        self.temp_dir_obj = None
        self.class_name = "Main"

    def _hash_code(self, code: str):
        return hashlib.sha256(code.encode()).hexdigest()

    def _cleanup_temp(self):
        if self.temp_dir_obj:
            try:
                self.temp_dir_obj.cleanup()
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}", file=sys.stderr)
        self.temp_dir_obj = None
        self.compiled_path = None

    async def run_code(self, code: str, test_cases: list, mode="run_all"):
        code_hash = self._hash_code(code)

        if mode == "reset":
            self.last_code_hash = None
            self.last_results = []
            self._cleanup_temp()
            yield {"results": [], "all_passed": True, "status": "reset"}
            return

        if mode == "run_failed":
            test_cases_to_run = [
                {"input": r["input"], "expected": r["expected"]}
                for r in self.last_results if not r.get("passed", False)
            ]
            if not test_cases_to_run:
                yield {"results": self.last_results, "all_passed": True, "status": "no_failed_tests"}
                return
        else:
            test_cases_to_run = test_cases

        if self.language == "python":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                    f.write(code)
                    self.compiled_path = f.name
                self.last_code_hash = code_hash

            if mode == "compile_only":
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return

            temp_dir = os.path.dirname(self.compiled_path)
            filename = os.path.basename(self.compiled_path)
            container_path = f"/workspace/{filename}"

            for case in test_cases_to_run:
                input_data = json.dumps(case["input"]).encode()
                try:
                    process = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{temp_dir}:/workspace",
                        "dsa-executor-image", "python3", container_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(input=input_data), timeout=2)
                    output = stdout.decode().strip()
                    error = stderr.decode().strip()
                    if error:
                        result = {"input": case["input"], "error": error, "passed": False}
                    else:
                        try:
                            output_val = json.loads(output)
                            expected_val = case["expected"]
                            passed = output_val == expected_val
                        except json.JSONDecodeError:
                            passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    process.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                yield result

        elif self.language == "java":
            code_lines = code.splitlines()
            import_lines = [l for l in code_lines if l.strip().startswith("import ") or l.strip().startswith("package ")]
            user_code_body = [l for l in code_lines if not (l.strip().startswith("import ") or l.strip().startswith("package "))]
            
            if not any("java.util.*" in l for l in import_lines):
                import_lines.append("import java.util.*;")
            if not any("java.util.Arrays" in l for l in import_lines):
                 import_lines.append("import java.util.Arrays;")


            if mode == "compile_only":
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return

            for case in test_cases_to_run:
                temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = temp_dir_obj.name
                case_input = case["input"]
                
                if not isinstance(case_input, dict):
                    yield {"input": case["input"], "error": "Java executor currently requires dictionary input.", "passed": False}
                    temp_dir_obj.cleanup()
                    continue

                variable_declarations = []
                solution_args = []
                
                def py_to_java_type(val):
                    if isinstance(val, bool): return "boolean"
                    if isinstance(val, int): return "int"
                    if isinstance(val, float): return "double"
                    if isinstance(val, str): return "String"
                    if isinstance(val, list):
                        if not val: return "Object[]"
                        if all(isinstance(i, int) for i in val): return "int[]"
                        if all(isinstance(i, str) for i in val): return "String[]"
                    return "Object"

                def py_to_java_value(val):
                    if isinstance(val, str): return json.dumps(val)
                    if isinstance(val, bool): return str(val).lower()
                    if isinstance(val, list):
                        if not val: return "new Object[]{}"
                        item_type = py_to_java_type(val[0]).replace("[]","")
                        return f"new {item_type}[]" + "{" + ", ".join(map(py_to_java_value, val)) + "}"
                    return str(val)

                for key, value in case_input.items():
                    java_type = py_to_java_type(value)
                    java_value = py_to_java_value(value)
                    variable_declarations.append(f"        {java_type} {key} = {java_value};")
                    solution_args.append(key)

                declarations_str = "\n".join(variable_declarations)
                args_str = ", ".join(solution_args)

                method_name_match = re.search(r"public\s+[\w<>\[\]]+\s+(\w+)\s*\(", code)
                method_name = method_name_match.group(1) if method_name_match else "solve"
                
                expected_output = case["expected"]
                if isinstance(expected_output, list):
                    print_statement = f"System.out.println(Arrays.toString(sol.{method_name}({args_str})));"
                else:
                    print_statement = f"System.out.println(sol.{method_name}({args_str}));"

                wrapper_code = f"""
public class Main {{
    public static void main(String[] args) {{
{declarations_str}
        Solution sol = new Solution();
        {print_statement}
    }}
}}"""
                full_code = "\n".join(import_lines) + "\n\n" + "\n".join(user_code_body) + "\n\n" + wrapper_code
                java_path = os.path.join(tmpdir, "Main.java")
                with open(java_path, "w") as f: f.write(full_code)

                try:
                    compile_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-v", f"{tmpdir}:/workspace", "dsa-executor-image",
                        "javac", "/workspace/Main.java",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    _, stderr = await compile_proc.communicate()
                    if compile_proc.returncode != 0:
                        yield {"input": case["input"], "error": f"Compilation error: {stderr.decode().strip()}", "passed": False}
                        temp_dir_obj.cleanup()
                        continue
                except Exception as e:
                    yield {"input": case["input"], "error": f"Compilation exception: {e}", "passed": False}
                    temp_dir_obj.cleanup()
                    continue

                try:
                    run_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-v", f"{tmpdir}:/workspace", "dsa-executor-image",
                        "java", "-cp", "/workspace", "Main",
                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(), timeout=2)
                    output = stdout.decode().strip()
                    error = stderr.decode().strip()

                    if error:
                        result = {"input": case["input"], "error": error, "passed": False}
                    else:
                        normalized_output = output.replace(" ", "").replace("\n", "")
                        expected_str = str(case["expected"]).replace(" ", "").replace("'", "\"")
                        if isinstance(case["expected"], list):
                            expected_str = "[" + ",".join(map(str, case["expected"])) + "]"
                            expected_str = expected_str.replace(" ", "")

                        passed = normalized_output == expected_str
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}

                except asyncio.TimeoutError:
                    run_proc.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                except Exception as e:
                    result = {"input": case["input"], "error": f"Runtime exception: {e}", "passed": False}
                
                yield result
                temp_dir_obj.cleanup()

        elif self.language == "cpp":
            if self.last_code_hash != code_hash or not self.compiled_path:
                self._cleanup_temp()
                self.temp_dir_obj = tempfile.TemporaryDirectory()
                tmpdir = self.temp_dir_obj.name
                cpp_path = os.path.join(tmpdir, "solution.cpp")
                exe_path = os.path.join(tmpdir, "solution.out")
                with open(cpp_path, "w") as f: f.write(code)
                compile_proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm", "-i", "-v", f"{tmpdir}:/workspace",
                    "dsa-executor-image", "g++", "-std=c++17", "/workspace/solution.cpp", "-o", "/workspace/solution.out",
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                _, stderr = await compile_proc.communicate()
                if compile_proc.returncode != 0:
                    error_msg = stderr.decode().strip()
                    self._cleanup_temp()
                    for case in test_cases_to_run:
                        yield {"input": case["input"], "error": f"Compilation error: {error_msg}", "passed": False}
                    return
                self.compiled_path = exe_path
                self.last_code_hash = code_hash

            if mode == "compile_only":
                yield {"results": [], "all_passed": True, "status": "compiled"}
                return

            temp_dir = os.path.dirname(self.compiled_path)
            exe_filename = os.path.basename(self.compiled_path)
            container_path = f"/workspace/{exe_filename}"
            for case in test_cases_to_run:
                input_data = json.dumps(case["input"]).encode()
                try:
                    run_proc = await asyncio.create_subprocess_exec(
                        "docker", "run", "--rm", "-i",
                        "-v", f"{temp_dir}:/workspace",
                        "dsa-executor-image", container_path,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(run_proc.communicate(input=input_data), timeout=2)
                    output = stdout.decode().strip()
                    error = stderr.decode().strip()
                    if error:
                        result = {"input": case["input"], "error": error, "passed": False}
                    else:
                        try:
                            output_val = json.loads(output)
                            expected_val = case["expected"]
                            passed = output_val == expected_val
                        except json.JSONDecodeError:
                            passed = output == str(case["expected"])
                        result = {"input": case["input"], "output": output, "expected": case["expected"], "passed": passed}
                except asyncio.TimeoutError:
                    run_proc.kill()
                    result = {"input": case["input"], "error": "Timeout", "passed": False}
                yield result

async def main():
    executors = {
        "python": CodeExecutor(language="python"),
        "java": CodeExecutor(language="java"),
        "cpp": CodeExecutor(language="cpp"),
    }
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            command = json.loads(line)
            language = command.get("language")
            if language not in executors:
                print(json.dumps({"error": f"Unsupported language: {language}", "passed": False}), flush=True)
                continue
            executor = executors[language]
            code = command.get("code", "")
            test_cases = command.get("test_cases", [])
            mode = command.get("mode", "run_all")
            runner = executor.run_code(code, test_cases, mode=mode)
            async for result in runner:
                print(json.dumps(result), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON command", "passed": False}), flush=True)
        except Exception as e:
            print(json.dumps({"error": f"An unexpected error occurred: {str(e)}", "passed": False}), flush=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

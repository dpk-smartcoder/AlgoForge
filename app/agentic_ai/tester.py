import asyncio
import json
import sys

async def test_java_executor():
    # Example Java code (user solution without main)
    java_code = """
import java.util.*;

class Solution {
    public long maximumActivationValue(int[] value, int[] limit) {
        long sum = 0;
        for (int v : value) sum += v;
        return sum;
    }
}
"""

    # Example test cases with input as dict {value: [...], limit: [...]}
    test_cases = [
        {
            "input": {"value": [1, 2, 3], "limit": [4, 5, 6]},
            "expected": "6"
        },
        {
            "input": {"value": [10, 20], "limit": [1, 2]},
            "expected": "30"
        },
        {
            "input": {"value": [0, 0, 0], "limit": [0, 0, 0]},
            "expected": "0"
        },
    ]

    # Prepare the command to send to the executor stdin
    command = {
        "language": "java",
        "code": java_code,
        "test_cases": test_cases,
        "mode": "run_all"
    }

    # Start your executor as a subprocess - update the command if needed
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "app/agentic_ai/executor.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Send the command as a JSON line
    cmd_str = json.dumps(command) + "\n"
    stdout, stderr = await proc.communicate(input=cmd_str.encode())

    if stderr:
        print("Executor stderr:", stderr.decode(), file=sys.stderr)

    # Output will be multiple JSON lines for each test case result
    # So we split output by lines and parse JSON
    lines = stdout.decode().strip().splitlines()
    for line in lines:
        try:
            res = json.loads(line)
            print("Test case result:", res)
        except Exception as e:
            print(f"Failed to parse line: {line} ({e})")

if __name__ == "__main__":
    asyncio.run(test_java_executor())
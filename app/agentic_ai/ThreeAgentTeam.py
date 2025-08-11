from app.agentic_ai.executor import CodeExecutor
from app.agentic_ai.team_class import AlgoForgeAgent
from app.agentic_ai.model_client import Model_Client
from dotenv import load_dotenv
import os
import json
import asyncio
import inspect
import difflib
import os
def safe_load_json(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        print(f"[WARNING] File not found: {path}. Using default.")
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse {path}: {e}. Using default.")
        return default
    except Exception as e:
        print(f"[ERROR] Unexpected error reading {path}: {e}. Using default.")
        return default

def normalize_test_cases(tc):
    if isinstance(tc, dict):
        return [tc]
    elif isinstance(tc, list):
        return [t for t in tc if isinstance(t, dict)]
    else:
        print("[WARNING] Invalid test_case format. Ignoring.")
        return []

# Load environment variables
load_dotenv()

API_KEY1=os.getenv("key1")
API_KEY2=os.getenv("key2")
API_KEY3=os.getenv("key3")
API_KEY4=os.getenv("key4")
model1=os.getenv("model1")
model2=os.getenv("model2")
model3=os.getenv("model3")
model4=os.getenv("model4")
language=os.getenv("lang")

# Initialize components
executor=CodeExecutor(language)
teamA=AlgoForgeAgent("A_Team",Model_Client(model=model1,API_KEY=API_KEY1).getClient(),executor,language)
teamB=AlgoForgeAgent("B_Team",Model_Client(model=model2,API_KEY=API_KEY2).getClient(),executor,language)
teamC=AlgoForgeAgent("C_Team",Model_Client(model=model3,API_KEY=API_KEY3).getClient(),executor,language)

data = safe_load_json("data.json", {"problem": {}})
randomTestCase = safe_load_json("random.json", {"test_case": []})

problem_data = data.get("problem", {})

# --- FIX: Ensure all parts of the prompt are strings ---
# Get the statement and constraint data
statement_text = problem_data.get("statement", "")
constraint_text = problem_data.get("constraint", "")

# Explicitly convert them to strings if they are not already
# This handles cases where the JSON has a list or other object instead of a string
if not isinstance(statement_text, str):
    statement_text = json.dumps(statement_text, indent=2)

if not isinstance(constraint_text, str):
    constraint_text = json.dumps(constraint_text, indent=2)
# --- END FIX ---

merged_test_cases = normalize_test_cases(problem_data.get("test_case", []))
merged_test_cases.extend(normalize_test_cases(randomTestCase.get("test_case", [])))

# Deduplicate merged_test_cases while preserving order
seen = set()
deduped_test_cases = []
for tc in merged_test_cases:
    try:
        tc_key = json.dumps(tc, sort_keys=True)
    except TypeError:
        tc_key = str(tc)
    if tc_key not in seen:
        seen.add(tc_key)
        deduped_test_cases.append(tc)
merged_test_cases = deduped_test_cases

# Convert the merged test cases list to a JSON formatted string for the prompt
# This part was already correct.
testcase_text = json.dumps(merged_test_cases, indent=2)

# Build the final problem prompt
problem_prompt = (
    os.getenv("Question_prompt", "") + statement_text +
    os.getenv("Constraint_prompt", "") + constraint_text +
    os.getenv("TestCase_prompt", "") + testcase_text
)

def generate_code_diff(old_code, new_code):
    """
    Generates a unified diff between two code versions as a string.
    """
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile="old_code",
        tofile="new_code",
        lineterm=""
    )
    return "\n".join(diff)

# --- Structured Team Workflow ---

# NOTE: This pipeline is async. It tolerates different executor return styles:
# - async generator (yields per-test result),
# - coroutine returning a dict/list,
# - or synchronous return (dict/list).
#
max_initial_refinements = 1
max_turns = 1
cross_pollinate_rounds =1

# Use merged test cases from both data.json and randomTestCase
# This variable correctly remains a list of dicts for the executor
test_cases = merged_test_cases

async def collect_test_results(code, timeout=10):
    """
    Calls executor.run_code(...) and collects results into a list of result dicts.
    Each result dict is expected to have a boolean 'passed' key when possible.
    Returns: (results_list, failed_list_as_json_string)
    timeout: seconds to wait for execution (default 10)
    """
    TIMEOUT = timeout
    runner = executor.run_code(code, test_cases, mode="run_all")

    results = []
    try:
        # case 1: async generator (yields results)
        if inspect.isasyncgen(runner):
            async def collect_all():
                out = []
                async for r in runner:
                    out.append(r)
                return out
            results = await asyncio.wait_for(collect_all(), timeout=TIMEOUT)
        # case 2: coroutine (await and inspect returned structure)
        elif asyncio.iscoroutine(runner):
            res = await asyncio.wait_for(runner, timeout=TIMEOUT)
            if isinstance(res, dict) and "results" in res:
                results = res["results"]
            elif isinstance(res, list):
                results = res
            else:
                results = [res]
        # case 3: synchronous return
        else:
            # Protect with asyncio.to_thread and timeout
            def sync_runner():
                res = runner
                if isinstance(res, dict) and "results" in res:
                    return res["results"]
                elif isinstance(res, list):
                    return res
                else:
                    return [res]
            results = await asyncio.wait_for(asyncio.to_thread(sync_runner), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        print("Test execution timed out")
        return [], "[]"
    except Exception as e:
        print(f"Error during test execution: {e}")
        return [], "[]"

    failed = [r for r in results if not r.get("passed", False)]
    failed_str = json.dumps(failed, indent=2)
    return results, failed_str

async def maybe_await_call(func, *args, **kwargs):
    """
    Call func(...). If it returns a coroutine, await it; otherwise return result directly.
    This allows agent methods to be either sync or async.
    """
    out = func(*args, **kwargs)
    if asyncio.iscoroutine(out):
        return await out
    return out

async def run_team_workflow(team):
    """
    Runs Phase 1 (generate + initial refinements) and Phase 2 (test & refine) for one team.
    Stores metadata on the team object:
      - team.current_code
      - team.last_results
      - team.failed_cases
      - team.solved (bool)
      - team.solved_code (if solved)
    """
    # PHASE 1: generate + initial refinements
    code = await team.generate_code(problem_prompt)
    for _ in range(max_initial_refinements):
        code = await maybe_await_call(team.refine_code_withoutCotext,problem_prompt, code)

    team.current_code = code
    team.last_results = []
    team.failed_cases = []
    team.solved = False

    # PHASE 2: test & refine until all pass or max_turns reached
    turn = 0
    while turn < max_turns:
        results, failed_str = await collect_test_results(team.current_code)
        team.last_results = results
        team.failed_cases = failed_str
        if not failed_str or failed_str == "[]":
            team.solved = True
            team.solved_code = team.current_code
            break
        # refine using failed cases context
        team.current_code = await maybe_await_call(
            team.refine_code_withContext,team.current_code, fail_logs=failed_str
        )
        turn += 1

    return team

async def main():
    teams = [teamA, teamB, teamC]
    solutions_log = []

    # Run all teams independently in parallel (Phase 1 + Phase 2)
    team_outcomes = await asyncio.gather(*(run_team_workflow(t) for t in teams))

    solved = [t for t in team_outcomes if getattr(t, "solved", False)]
    unsolved = [t for t in team_outcomes if not getattr(t, "solved", False)]

    # If any solved, accept those solutions right away (and attempt cross-pollination to help unsolved)
    if solved:
        print(f"Found {len(solved)} solution(s) from independent runs.")
        for t in solved:
            print(f"\n--- Solution from {getattr(t, 'name', str(t))} ---")
            print(getattr(t, "solved_code", t.current_code))
            solutions_log.append({
                "team": getattr(t, "name", str(t)),
                "code": getattr(t, "solved_code", t.current_code),
                "status": "solved"
            })

        # Best-effort: try to help unsolved teams using the successful teams' code
        for _ in range(cross_pollinate_rounds):
            newly_solved = []
            for src in solved:
                for tgt in list(unsolved):  # iterate over a copy as we may remove entries
                    diff_summary = generate_code_diff(tgt.current_code, src.solved_code)
                    refined_code = await maybe_await_call(
                        tgt.refine_code_withContext,
                        f"""Your last attempt failed with the following cases:
{tgt.failed_cases}

Here is the difference between your code and a working solution:
{diff_summary}

Update your code by integrating the necessary logic fixes from the working solution while keeping correct existing parts.""",
                        fail_logs=tgt.failed_cases
                    )
                    tgt.current_code = refined_code
                    results, failed_str = await collect_test_results(tgt.current_code)
                    tgt.last_results = results
                    tgt.failed_cases = failed_str
                    if not failed_str or failed_str == "[]":
                        tgt.solved = True
                        tgt.solved_code = tgt.current_code
                        newly_solved.append(tgt)
                        unsolved.remove(tgt)
            if not newly_solved:
                break
            solved.extend(newly_solved)
            for t in newly_solved:
                solutions_log.append({
                    "team": getattr(t, "name", str(t)),
                    "code": getattr(t, "solved_code", t.current_code),
                    "status": "solved"
                })

        # Final behavior: if single solver -> return single; if multiple -> return all.
        if len(solved) == 1:
            winner = solved[0]
            print(f"\nReturning single solution from {getattr(winner, 'name', str(winner))}.")
        else:
            print("\nMultiple successful solutions found; returning all successful solutions.")
        with open("solutions.json", "w") as f:
            json.dump(solutions_log, f, indent=2)
        return

    # No team solved independently -> round-robin cross-pollination attempt
    print("No team solved independently. Starting round-robin cross-pollination.")
    has_any_solved_code = any(hasattr(t, "solved_code") and t.solved_code is not None for t in teams)
    if not has_any_solved_code:
        print("No solved code available — using latest failed attempts for cross-pollination.")
        
    for _ in range(cross_pollinate_rounds):
        any_new = False
        for src in teams:
            # Pick solved code if available, else current attempt
            src_code_to_share = src.solved_code if getattr(src, "solved_code", None) else getattr(src, "current_code", "")
            if not src_code_to_share:
                continue
            for tgt in teams:
                if src is tgt:
                    continue
                diff_summary = generate_code_diff(tgt.current_code, src_code_to_share)
                refined_code = await maybe_await_call(
                    tgt.refine_code_withContext,
                    f"""Your last attempt failed with the following cases:
{tgt.failed_cases}

Here is the difference between your code and another attempt (which may be working or closer to working):
{diff_summary}

Update your code by integrating the useful logic from this attempt while keeping correct existing parts.""",
                    fail_logs=tgt.failed_cases
                )
                tgt.current_code = refined_code
                results, failed_str = await collect_test_results(tgt.current_code)
                tgt.last_results = results
                tgt.failed_cases = failed_str
                if (not failed_str or failed_str == "[]") and not getattr(tgt, "solved", False):
                    tgt.solved = True
                    tgt.solved_code = tgt.current_code
                    any_new = True
        if any_new:
            break

    solved = [t for t in teams if getattr(t, "solved", False)]
    if solved:
        print(f"After cross-pollination, {len(solved)} solution(s) found.")
        for t in solved:
            print(f"\n--- Solution from {getattr(t, 'name', str(t))} ---")
            print(getattr(t, "solved_code", t.current_code))
            solutions_log.append({
                "team": getattr(t, "name", str(t)),
                "code": getattr(t, "solved_code", t.current_code),
                "status": "solved"
            })
    else:
        print("No solutions found after cross-pollination. Returning best-effort latest attempts from each team:")
        for t in teams:
            print(f"\n--- Latest attempt from {getattr(t, 'name', str(t))} ---")
            print(getattr(t, "current_code", "<no code>"))
    with open("solutions.json", "w") as f:
        json.dump(solutions_log, f, indent=2)

if __name__ == "__main__":
    import sys
    async def _main_and_log_all():
        teams = [teamA, teamB, teamC]
        solutions_log = []
        # Run all teams independently in parallel (Phase 1 + Phase 2)
        team_outcomes = await asyncio.gather(*(run_team_workflow(t) for t in teams))

        solved = [t for t in team_outcomes if getattr(t, "solved", False)]
        unsolved = [t for t in team_outcomes if not getattr(t, "solved", False)]

        # Helper to extract summary from team's last code output, if available
        def extract_summary(team):
            # Try to get summary from last_results, if any result has a 'summary' field
            # Or from a 'summary' field in a code output JSON, if such exists
            # But as we don't have code output JSON, fallback to ""
            # If team.last_results is a list of dicts, look for 'summary' field
            if hasattr(team, "last_results") and isinstance(team.last_results, list):
                for r in team.last_results:
                    if isinstance(r, dict) and "summary" in r:
                        return r["summary"]
            # fallback
            return ""

        # If any solved, accept those solutions right away (and attempt cross-pollination to help unsolved)
        if solved:
            print(f"Found {len(solved)} solution(s) from independent runs.")
            for t in solved:
                summary = extract_summary(t)
                print(f"\n--- Solution from {getattr(t, 'name', str(t))} ---")
                print(getattr(t, "solved_code", t.current_code))
                if summary:
                    print(f"Summary: {summary}")
                solutions_log.append({
                    "team": getattr(t, "name", str(t)),
                    "code": getattr(t, "solved_code", t.current_code),
                    "status": "solved",
                    "summary": summary
                })

            # Best-effort: try to help unsolved teams using the successful teams' code
            for _ in range(cross_pollinate_rounds):
                newly_solved = []
                for src in solved:
                    for tgt in list(unsolved):  # iterate over a copy as we may remove entries
                        refined_code = await maybe_await_call(
                            tgt.refine_code_withContext,
                            f"This was my last attempt that failed:\n{tgt.current_code}\n\nHere is a successful solution from another team for you to learn from:\n{src.solved_code}",
                            fail_logs=tgt.failed_cases
                        )
                        tgt.current_code = refined_code
                        results, failed_str = await collect_test_results(tgt.current_code)
                        tgt.last_results = results
                        tgt.failed_cases = failed_str
                        if not failed_str or failed_str == "[]":
                            tgt.solved = True
                            tgt.solved_code = tgt.current_code
                            newly_solved.append(tgt)
                            unsolved.remove(tgt)
                if not newly_solved:
                    break
                solved.extend(newly_solved)
                for t in newly_solved:
                    summary = extract_summary(t)
                    print(f"\n--- Solution from {getattr(t, 'name', str(t))} ---")
                    print(getattr(t, "solved_code", t.current_code))
                    if summary:
                        print(f"Summary: {summary}")
                    solutions_log.append({
                        "team": getattr(t, "name", str(t)),
                        "code": getattr(t, "solved_code", t.current_code),
                        "status": "solved",
                        "summary": summary
                    })

            # At this point, add any remaining unsolved teams to the log with latest code
            for t in unsolved:
                summary = extract_summary(t)
                print(f"\n--- Latest attempt from {getattr(t, 'name', str(t))} ---")
                print(getattr(t, "current_code", "<no code>"))
                if summary:
                    print(f"Summary: {summary}")
                solutions_log.append({
                    "team": getattr(t, "name", str(t)),
                    "code": getattr(t, "current_code", "<no code>"),
                    "status": "unsolved",
                    "summary": summary
                })

            with open("solutions.json", "w") as f:
                json.dump(solutions_log, f, indent=2)
            return

        # No team solved independently -> round-robin cross-pollination attempt
        print("No team solved independently. Starting round-robin cross-pollination.")
        has_any_solved_code = any(hasattr(t, "solved_code") and t.solved_code is not None for t in teams)
        if not has_any_solved_code:
            print("No solved code available — using latest failed attempts for cross-pollination.")

        for _ in range(cross_pollinate_rounds):
            any_new = False
            for src in teams:
                # Pick solved code if available, else current attempt
                src_code_to_share = src.solved_code if getattr(src, "solved_code", None) else getattr(src, "current_code", "")
                if not src_code_to_share:
                    continue
                for tgt in teams:
                    if src is tgt:
                        continue
                    refined_code = await maybe_await_call(
                        tgt.refine_code_withContext,
                        f"This was my last attempt that failed:\n{tgt.current_code}\n\nHere is another attempt from a different team for you to learn from:\n{src_code_to_share}",
                        fail_logs=tgt.failed_cases
                    )
                    tgt.current_code = refined_code
                    results, failed_str = await collect_test_results(tgt.current_code)
                    tgt.last_results = results
                    tgt.failed_cases = failed_str
                    if (not failed_str or failed_str == "[]") and not getattr(tgt, "solved", False):
                        tgt.solved = True
                        tgt.solved_code = tgt.current_code
                        any_new = True
            if any_new:
                break

        solved = [t for t in teams if getattr(t, "solved", False)]
        if solved:
            print(f"After cross-pollination, {len(solved)} solution(s) found.")
            for t in solved:
                summary = extract_summary(t)
                print(f"\n--- Solution from {getattr(t, 'name', str(t))} ---")
                print(getattr(t, "solved_code", t.current_code))
                if summary:
                    print(f"Summary: {summary}")
                solutions_log.append({
                    "team": getattr(t, "name", str(t)),
                    "code": getattr(t, "solved_code", t.current_code),
                    "status": "solved",
                    "summary": summary
                })
        else:
            print("No solutions found after cross-pollination. Returning best-effort latest attempts from each team:")
            for t in teams:
                print(f"\n--- Latest attempt from {getattr(t, 'name', str(t))} ---")
                print(getattr(t, "current_code", "<no code>"))

            # --- Rescue Mode: Try a final agent with full context if all teams failed ---
            # Only activate if truly no team solved
            if not solved:
                print("\n[Rescue Mode] Activating Rescue Team for one last attempt...")
                # Gather problem statement, all failed cases, and last code attempts
                all_failed_cases = []
                all_last_codes = []
                for t in teams:
                    name = getattr(t, "name", str(t))
                    failed = getattr(t, "failed_cases", "")
                    code = getattr(t, "current_code", "")
                    all_failed_cases.append(f"Team {name} failed cases:\n{failed}")
                    all_last_codes.append(f"Team {name} last code:\n{code}")
                rescue_context = "\n\n".join(all_failed_cases + all_last_codes)
                # Use model1/API_KEY1 for rescue agent
                rescue_agent = AlgoForgeAgent(
                    "Rescue_Team",
                    Model_Client(model=model1, API_KEY=API_KEY1).getClient(),
                    executor,
                    language
                )
                rescue_prompt = (
                    "All previous team attempts to solve the following problem have failed all test cases. "
                    "You are the Rescue Team. Please carefully review the problem, the failed test cases, and the code attempts below. Use deep research if needed."
                    "Use previous attempts only to understand mistakes, do not copy any code directly. Write a fresh solution from scratch.\n"
                    "Write a fresh, correct, and working solution from scratch (do NOT copy the previous code), ensuring it passes all provided test cases.\n\n"
                    "PROBLEM:\n"
                    f"{problem_prompt}\n\n"
                    f"{rescue_context}\n"
                    "Respond ONLY with the complete code for the solution."
                )
                rescue_code = await rescue_agent.generate_code(rescue_prompt)
                rescue_results, rescue_failed_str = await collect_test_results(rescue_code, timeout=20)
                passed_all = not rescue_failed_str or rescue_failed_str == "[]"
                rescue_status = "solved" if passed_all else "unsolved"
                rescue_source = "rescue_mode" if passed_all else "rescue_mode_attempt"
                print(f"\n--- Rescue Team Attempt ---")
                print(rescue_code)
                if passed_all:
                    print("[Rescue Mode] Rescue Team SOLVED the problem!")
                else:
                    print("[Rescue Mode] Rescue Team attempt did NOT solve all test cases.")

                # If failed, allow one refinement retry
                retry_code = None
                retry_results = None
                retry_failed_str = None
                retry_status = None
                if not passed_all:
                    retry_code = await rescue_agent.refine_code_withContext(rescue_code, fail_logs=rescue_failed_str)
                    retry_results, retry_failed_str = await collect_test_results(retry_code, timeout=20)
                    retry_passed_all = not retry_failed_str or retry_failed_str == "[]"
                    retry_status = "solved" if retry_passed_all else "unsolved"
                    retry_source = "rescue_mode_refinement" if retry_passed_all else "rescue_mode_final"
                    print(f"\n--- Rescue Team Refinement Attempt ---")
                    print(retry_code)
                    if retry_passed_all:
                        print("[Rescue Mode] Rescue Team SOLVED the problem on refinement!")
                    else:
                        print("[Rescue Mode] Rescue Team refinement attempt did NOT solve all test cases.")
                    solutions_log.append({
                        "team": "Rescue_Team",
                        "code": retry_code,
                        "status": retry_status,
                        "source": retry_source,
                        "test_results": retry_results,
                        "reason": "All teams failed after cross-pollination",
                        "context_length_used": len(rescue_prompt)
                    })
                else:
                    solutions_log.append({
                        "team": "Rescue_Team",
                        "code": rescue_code,
                        "status": rescue_status,
                        "source": rescue_source,
                        "test_results": rescue_results,
                        "reason": "All teams failed after cross-pollination",
                        "context_length_used": len(rescue_prompt)
                    })

        # At this point, add all teams' latest attempts to the log (including unsolved)
        already_logged = {entry["team"] for entry in solutions_log}
        for t in teams:
            if getattr(t, "solved", False) and getattr(t, "name", str(t)) in already_logged:
                continue  # already logged above
            summary = extract_summary(t)
            print(f"\n--- Latest attempt from {getattr(t, 'name', str(t))} ---")
            print(getattr(t, "current_code", "<no code>"))
            if summary:
                print(f"Summary: {summary}")
            solutions_log.append({
                "team": getattr(t, "name", str(t)),
                "code": getattr(t, "solved_code", t.current_code) if getattr(t, "solved", False) else getattr(t, "current_code", "<no code>"),
                "status": "solved" if getattr(t, "solved", False) else "unsolved",
                "summary": summary
            })
        with open("solutions.json", "w") as f:
            json.dump(solutions_log, f, indent=2)

    asyncio.run(_main_and_log_all())
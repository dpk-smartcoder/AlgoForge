from app.agentic_ai.executor import CodeExecutor
from app.agentic_ai.team_class import AlgoForgeAgent
from app.agentic_ai.model_client import Model_Client
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY1=os.getenv("key1")
API_KEY2=os.getenv("key2")
API_KEY3=os.getenv("key3")
model1=os.getenv("model1")
model2=os.getenv("model2")
model3=os.getenv("model3")

language=os.getenv("lang")

executor=CodeExecutor(language)
teamA=AlgoForgeAgent("A_Team",Model_Client(model=model1,API_KEY=API_KEY1),executor)
teamB=AlgoForgeAgent("B_Team",Model_Client(model=model2,API_KEY=API_KEY2),executor)
teamC=AlgoForgeAgent("C_Team",Model_Client(model=model3,API_KEY=API_KEY3),executor)
import json
# Load JSON data from file path specified in .env
json_path = os.getenv("json_file_path", "data.json")
with open(json_path, "r") as f:
    data = json.load(f)

# Safely extract values from JSON assuming keys 'statement', 'constraint', 'test_case'
statement_text = data.get("statement", "")
constraint_text = data.get("constraint", "")
testcase_text = data.get("test_case", "")

# Build the problem prompt
problem_prompt = (
    os.getenv("Question_prompt", "") + statement_text +
    os.getenv("Constraint_prompt", "") + constraint_text +
    os.getenv("TestCase_prompt", "") + testcase_text
)


# --- Structured Team Workflow ---

# NOTE: This pipeline is async. It tolerates different executor return styles:
# - async generator (yields per-test result),
# - coroutine returning a dict/list,
# - or synchronous return (dict/list).
#
# TODO: populate `test_cases` with your actual tests:
# test_cases = [{"input": "...", "expected": "..."}, ...]
max_initial_refinements = 5
max_turns = 10
cross_pollinate_rounds = 3

test_cases = []  # TODO: put your real test-cases here

import asyncio
import inspect

async def collect_test_results(code):
    """
    Calls executor.run_code(...) and collects results into a list of result dicts.
    Each result dict is expected to have a boolean 'passed' key when possible.
    Returns: (results_list, failed_list)
    """
    runner = executor.run_code(code, test_cases, mode="run_all")

    results = []
    # case 1: async generator (yields results)
    if inspect.isasyncgen(runner):
        async for r in runner:
            results.append(r)
    # case 2: coroutine (await and inspect returned structure)
    elif asyncio.iscoroutine(runner):
        res = await runner
        if isinstance(res, dict) and "results" in res:
            results = res["results"]
        elif isinstance(res, list):
            results = res
        else:
            results = [res]
    # case 3: synchronous return
    else:
        res = runner
        if isinstance(res, dict) and "results" in res:
            results = res["results"]
        elif isinstance(res, list):
            results = res
        else:
            results = [res]

    failed = [r for r in results if not r.get("passed", False)]
    return results, failed

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
    code = team.generate_code("")
    for _ in range(max_initial_refinements):
        code = await maybe_await_call(team.refine_code_withoutCotext,problem_prompt, code)

    team.current_code = code
    team.last_results = []
    team.failed_cases = []
    team.solved = False

    # PHASE 2: test & refine until all pass or max_turns reached
    turn = 0
    while turn < max_turns:
        results, failed = await collect_test_results(team.current_code)
        team.last_results = results
        team.failed_cases = failed
        if not failed:
            team.solved = True
            team.solved_code = team.current_code
            break
        # refine using failed cases context
        team.current_code = await maybe_await_call(
            team.refine_code_withContext,problem_prompt, team.current_code, fail_logs=failed
        )
        turn += 1

    return team

async def main():
    teams = [teamA, teamB, teamC]

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

        # Best-effort: try to help unsolved teams using the successful teams' code
        for _ in range(cross_pollinate_rounds):
            newly_solved = []
            for src in solved:
                for tgt in list(unsolved):  # iterate over a copy as we may remove entries
                    refined_code = await maybe_await_call(
                        tgt.refine_code_withContext, src.solved_code, tgt.current_code, fail_logs=tgt.failed_cases
                    )
                    tgt.current_code = refined_code
                    results, failed = await collect_test_results(tgt.current_code)
                    tgt.last_results = results
                    tgt.failed_cases = failed
                    if not failed:
                        tgt.solved = True
                        tgt.solved_code = tgt.current_code
                        newly_solved.append(tgt)
                        unsolved.remove(tgt)
            if not newly_solved:
                break
            solved.extend(newly_solved)

        # Final behavior: if single solver -> return single; if multiple -> return all.
        if len(solved) == 1:
            winner = solved[0]
            print(f"\nReturning single solution from {getattr(winner, 'name', str(winner))}.")
        else:
            print("\nMultiple successful solutions found; returning all successful solutions.")
        return

    # No team solved independently -> round-robin cross-pollination attempt
    print("No team solved independently. Starting round-robin cross-pollination.")
    for _ in range(cross_pollinate_rounds):
        any_new = False
        for src in teams:
            for tgt in teams:
                if src is tgt:
                    continue
                tgt.current_code = await maybe_await_call(
                    tgt.refine_code_withContext, src.current_code, tgt.current_code, fail_logs=tgt.failed_cases
                )
                results, failed = await collect_test_results(tgt.current_code)
                tgt.last_results = results
                tgt.failed_cases = failed
                if not failed and not getattr(tgt, "solved", False):
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
    else:
        print("No solutions found after cross-pollination. Returning best-effort latest attempts from each team:")
        for t in teams:
            print(f"\n--- Latest attempt from {getattr(t, 'name', str(t))} ---")
            print(getattr(t, "current_code", "<no code>"))

if __name__ == "__main__":
    asyncio.run(main())
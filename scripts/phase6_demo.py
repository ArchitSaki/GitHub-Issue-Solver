"""
phase6_demo.py — long-term memory in action. Run with:

    python -m scripts.phase6_demo

Story:
  1. We "remember" a few issues we solved in the PAST.
  2. A NEW issue arrives.
  3. Memory recalls the most similar past issue + its solution, so the agent can
     reuse that experience instead of starting from zero.
"""

from app.memory.store import get_memory


if __name__ == "__main__":
    memory = get_memory()

    # STEP 1: seed some "already solved" issues (stable ids => no duplicates on re-run).
    print("Saving past solved issues into long-term memory...")
    memory.remember(
        issue_summary="App crashes on login when the email field is empty",
        solution="Added an input validation check that rejects empty email before use.",
        memory_id="issue-login-empty-email",
    )
    memory.remember(
        issue_summary="Dark mode toggle does not save the user's preference",
        solution="Persisted the theme choice in localStorage and read it on startup.",
        memory_id="issue-dark-mode-persist",
    )
    memory.remember(
        issue_summary="Export to CSV button is slow for large tables",
        solution="Streamed rows and generated the CSV in chunks instead of all at once.",
        memory_id="issue-csv-export-slow",
    )

    # STEP 2: a NEW issue comes in (worded differently from the saved one).
    new_issue = "Signing in with a blank email address makes the app throw an error"
    print(f"\nNEW ISSUE: {new_issue}\n")

    # STEP 3: recall similar past experience.
    hits = memory.recall(new_issue)
    print(f"Recalled {len(hits)} similar past issue(s):\n")
    for i, h in enumerate(hits, 1):
        print(f"  {i}. PAST ISSUE : {h['past_issue']}")
        print(f"     PAST FIX   : {h['past_solution']}\n")

    print("Notice: the empty-email issue was recalled even though the wording differs.")
    print("[DONE] Phase 6: the system remembers and reuses past solutions.")

# A Short Intro to Test Suites

> **TL;DR** — Crash-course on what unit tests are, why every software firm uses them, and an intro to pytest in Python.

If you've mostly coded solo — class projects or hobby stuff — you may never have needed tests. Your code either worked or it didn't, and you were the only person touching it. On a **team** where several people push to the same repo, that doesn't work:

- You could easily push code that unintentionally breaks someone else's.
- Team repos are large — you won't know the ins and outs of everyone's part of the project.

That's why real companies use test suites. Every professional company making software does this, so it's worth mastering and making part of your workflow now. This guide is a quick intro.

## What a test suite is

A test suite is a collection of small programs that run *your* code with known inputs and check the output is what you expect. Instead of running your program and eyeballing the result, each test makes one specific claim — "a course the student already completed should come back as `fail`" — and the computer verifies it.

- One command runs all of them.
- **Green** = everything still behaves.
- **Red** = points at exactly which unit tests broke.

## Why should I care? How are they used in practice?

**You run the whole suite before every push to GitHub.** If the tests pass, you're safe to push. Tests protect code in *two directions*:

- **You didn't break anyone else's code.** You might have touched only one function, but if a hundred tests still pass, the rest of the system still works the way everyone expects.
- **Future contributors won't unintentionally break *your* code.** The tests you write today act as tripwires — if someone later changes something that breaks your logic, their test run goes red *before* it ships. You're protecting your work for people who've never even read it.

Real-world software leans on this hard:

- Production codebases often have **hundreds or thousands** of tests running on every change.
- That's not overkill — it's what lets a big team move fast without constantly breaking each other's work.

## What a test looks like

Here's a real one, checking that if a student requests to register for a course they already completed, the program should show a failure:

```python
from validate_next_semester import validate_next_semester

def test_completed_course_is_rejected():
    stars = {"completedCourses": [{"code": "CSCI 104"}],
             "inProgressCourses": [], "classLevel": "Junior"}
    catalog = {"courses": {"CSCI 104": {"units": 4, "sections": {}}}}

    result = validate_next_semester(["CSCI 104"], stars, catalog)

    course = result.course_results[0]
    assert course.status == "fail"
    assert any("already completed" in r for r in course.reasons)
```

This test checks one specific piece of logic, and reads top-to-bottom like plain English:

- **Set up:** a student who already took CSCI 104.
- **Run:** call the validator on that course.
- **Check:** the result's status is `"fail"` and it says why.

> [!WARNING]
> **⚠️ Potential Gotchya**
>
> This test *passing* means the validator correctly returned `"fail"`. "Fail" here is the validator's *answer* (this course isn't allowed) — not the test's verdict. A **green** (passing) test is confirming your code produced the **failure** it was supposed to. Test-passes-because-code-says-fail feels backwards at first, but it clicks quickly.

## Unit tests in Python: pytest

Use **pytest**. It's the modern standard for Python: plain functions and `assert`, almost no boilerplate, and clear failure messages. Install it with `pip install pytest`, put your tests in files named `test_*.py`, and run `pytest` from the project folder — it finds and runs them all.

Running the whole suite looks like this:

```console
$ pip install pytest        # one-time setup
$ pytest                    # discovers and runs every test_*.py in this folder and below

========================= test session starts =========================
collected 12 items

test_validate_next_semester.py ...........F                    [100%]

============================== FAILURES ===============================
______________ test_time_conflict_warns_on_any_overlap ________________
...
======================= short test summary info =======================
FAILED test_validate_next_semester.py::test_time_conflict_warns_on_any_overlap
==================== 1 failed, 11 passed in 0.09s =====================
```

Each `.` is a passing test, `F` is a failure, and the summary at the bottom tells you exactly which test broke. A clean run ends in all passes — that's your green light to push.

## Smoke tests — useful, but don't stop there

A *smoke test* just checks that your code runs end-to-end without crashing — it doesn't verify the answer is *correct*. (The name comes from hardware: plug it in and see if smoke comes out.) The current `__main__` block that runs the validator and prints the result is basically a smoke test: it tells you the thing executes, and nothing more.

- **AI assistants love to write these** — they're quick and always look productive.
- But a smoke test passes even if the logic is completely wrong, as long as nothing errors out.
- They're a fine *first* check, not a substitute for tests that assert specific expected results.

**Rule of thumb:** keep a smoke test or two for "does it even run," but the bulk of your suite should assert actual behavior (status is `X`, reason contains `Y`) like the example above.

## A few good habits

- One behavior per test, with a descriptive name like `test_400_level_blocked_for_sophomore` — when it fails, the name alone tells you what broke.
- Test the things that can go *wrong*, not just the happy path. Every bug you fix should get a test so it can never quietly come back.
- Keep each test's input small — only the fields that test actually needs.
- Keep tests independent — no shared state between them.

## Writing tests with an AI assistant is easy — no excuse to skip them

AI coding assistants are *great* at writing tests, so the effort barrier is basically gone. The trick is that **you** stay in charge of what's being tested — the AI writes the code, you decide the intent. Key steps:

- **Agree on what each test should check** *before* it writes anything — e.g. "a course the student already completed should come back as `fail`." One behavior per test.
- **Decide how the test gets its data** — a small inline example (like the snippet above), or loading a shared mock/fixture file. Be explicit so it doesn't invent a data shape.
- **Ask for the failure cases too**, not just the happy path — the edge cases and known bugs.
- **Read what it produces.** Make sure each test asserts the thing you actually care about, and that you understand why it passes.

### ⚠️ But don't let the AI "fix" tests by changing them

If a test is failing, **do not let the AI rebase, delete, or rewrite the test to make it pass** — and don't do it yourself — unless you genuinely understand *why* the test is wrong. A failing test is usually telling you your new code broke something real. "Fixing" it by editing the test throws away the exact protection the suite exists to provide. Change a test only when the expected behavior has *deliberately* changed and you can explain the change.

## Where to learn more

- **pytest — Get Started:** https://docs.pytest.org/en/stable/getting-started.html
- **pytest — full docs & how-to guides:** https://docs.pytest.org/en/stable/
- **Real Python — Getting Started With Testing in Python:** https://realpython.com/python-testing/
- **Real Python — pytest tutorial (fixtures, parametrize, more):** https://realpython.com/pytest-python-testing/
- **pytest — "Anatomy of a test":** https://docs.pytest.org/en/stable/explanation/anatomy.html

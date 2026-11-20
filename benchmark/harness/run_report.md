# Run report

Every benchmark run, of every task, ends with a short report. The harness gives the agent
the text below with every task's prompt, the same text for every task, so no task's prompt
has to ask for it and none asks for more than any other.

The report says whether the run finished and whether the input could support the task. The
text says what to write, not how to judge it or what to do about it: whether to look at
the input, and whether to go on from one the agent doubts, are left to the agent.

`grade_wrapper.py` reads the report of every run and keeps it in the envelope. It grades it
only for a task whose manifest entry names the report as its `record`: on a case whose
input cannot support the task, the report is the graded answer, and whether the run went on
to write an output is recorded beside it, not graded; on any other case, calling the input
unusable fails the case. On every other task the report is kept and the output is scored
whatever it says.

## Text given to the agent

```text
RUN REPORT. Whatever the outcome, end the run by writing report.json in the folder your
task's results go to, with exactly these fields:

  completed      true if you produced everything the task asks for, false if not
  input_usable   true if the input you were given could support the task, false if not
  reason         one sentence on the outcome
```

## Fields

| field | type | read by the grader |
|---|---|---|
| `completed` | JSON boolean | kept in the envelope, not graded |
| `input_usable` | JSON boolean | graded where the task's manifest entry has `record`, kept everywhere else; a string or a number is no answer |
| `reason` | string | kept in the envelope, not graded |

The report sits at `submissions/<task_id>/<case>/report.json` for a task graded per case,
and at `submissions/<task_id>/report.json` for a task with one reference.

# Agentic Study Assistant

A lightweight, robust, and verifiable **Agentic AI** task-planning assistant developed for a college Computer Science & Engineering (CSE) assignment.

The assistant accepts natural-language study goals, parses user intent deterministically, selects appropriate local tools, executes state changes, logs observable traces, and delivers human-readable output alongside schema-compliant JSON.

---

## 1. Project Objective

The primary objective of this project is to demonstrate the fundamental architectural principles of an **Agentic AI** system—specifically the **Plan → Act → Observe → Evaluate** lifecycle—without requiring third-party cloud APIs, paid tokens, or external models.

---

## 2. Problem Statement & Proposed Solution

### The Problem
College students struggle to manage competing academic workloads across subjects with varying deadlines and priorities. Traditional to-do apps are passive and lack contextual reasoning: they do not calculate available study time, prioritize urgent deadlines, or produce an actionable schedule for a dedicated study block.

### The Proposed Solution
The **Agentic Study Assistant** introduces an autonomous agent layer that:
1. **Understands Goals**: Interprets free-form requests such as adding topics, requesting schedules, or completing assignments.
2. **Prioritizes Intelligently**: Ranks tasks based on academic priority (`high` > `medium` > `low`), deadlines (earlier ISO due dates first), and time constraints.
3. **Packs Study Sessions**: Generates bounded, minute-by-minute study plans that fit strictly within the student's available time.
4. **Maintains Auditability**: Emits a transparent action-and-observation trace for every decision and tool execution.

---

## 3. Features & Supported Commands

### Core Capabilities
- **Task Management**: Create tasks with titles, estimated durations (minutes), priority levels, and optional due dates.
- **Strict Input Validation**: Rejects zero or negative durations, invalid priorities, and malformed dates.
- **Intelligent Session Planning**: Schedules high-priority and urgent tasks greedily within the student's available study window.
- **Flexible Completion**: Mark tasks done by either **1-based index** (`complete 1`) or **title substring** (`complete DBMS`).
- **Resilient Persistence**: Auto-saves and loads state from `data/tasks.json`, with graceful recovery from corrupted files.
- **Observable Action Traces**: Logs every tool call and observation; resets cleanly between turns.
- **Dual Output Modes**: Standard human-readable console output and formal schema-compliant JSON via `--json`.

### Supported Natural-Language Commands

| Intent | Command Syntax & Variations | Example |
|---|---|---|
| **Add Task** | `add <title> [for <minutes> min] [priority <level>] [due <YYYY-MM-DD>]` | `add Revise OS for 45 minutes priority high due 2026-10-25` |
| **Plan Session** | `plan <minutes> minutes` / `study for <minutes> mins` / `schedule <minutes> min` | `plan 120 minutes` |
| **List Tasks** | `list tasks` / `list` / `show tasks` / `status` | `list tasks` |
| **Complete Task** | `complete <id/fragment>` / `mark <id> as done` / `done <id>` | `complete 1` or `mark DBMS as done` |
| **Help & Exit** | `help` / `quit` / `exit` | `help` |

---

## 4. System Architecture & Schema Description

### Architecture Overview
The system is built around a decoupled three-tier architecture:
1. **Agent Orchestrator (`StudyAgent`)**: Manages the Plan-Act-Observe-Evaluate loop, input validation, and trace collection.
2. **Tool Execution Layer (`StudyTools`)**: Modular functions (`add_task`, `make_plan`, `list_tasks`, `complete_task`).
3. **Persistence Layer**: Local JSON storage in `data/tasks.json` with error handling.

For complete architectural details and the Mermaid diagram, see [`architecture.md`](architecture.md).

### Schema Description (`schema.json`)
The structured output adheres to JSON Schema Draft 2020-12 in [`schema.json`](schema.json):
- **`goal`** (`string`, required): The raw user prompt.
- **`message`** (`string`): The formatted terminal output message.
- **`plan`** (`array`, required): Scheduled tasks fitting within the session limit.
  - Required fields: `task`, `minutes` (>= 1), `priority` (`"high" | "medium" | "low"`).
  - Optional field: `due_date` (`YYYY-MM-DD` or null).
- **`tool_trace`** (`array`, required): List of executed tool calls, each containing:
  - `tool`: Function name executed.
  - `observation`: String result produced by the tool.
- **`tasks`** (`array`): Full list of all persisted task records with `status` (`"pending" | "done"`).

---

## 5. Technologies Used

- **Language**: Python 3.10+ (tested on Python 3.11.9)
- **Standard Library Modules**:
  - `dataclasses`: Strongly typed domain model (`Task`).
  - `argparse`: Command-line interface and flag handling.
  - `json`: Serialization, deserialization, and formatted tracing.
  - `re`: Regular-expression-based token extraction.
  - `datetime`: ISO 8601 calendar date validation.
  - `pathlib`: Cross-platform filesystem path resolution.
  - `unittest`: Automated testing suite.
  - `tempfile`: Isolated testing sandbox.
- **Optional / Dev Dependency**:
  - `jsonschema>=4.0.0`: Formal JSON Schema Draft 2020-12 validation (with built-in fallback).

---

## 6. Installation & Execution on Windows

### Prerequisites
- Windows 10 / 11
- Python 3.10 or higher installed with `Add Python to PATH` checked.

### Setup Instructions
1. Open PowerShell or Command Prompt.
2. Navigate to the project directory:
   ```powershell
   cd "c:\Users\user\Downloads\agentic ai"
   ```
3. (Optional) Install `jsonschema` for formal schema validation in tests:
   ```powershell
   pip install -r requirements.txt
   ```
   *(Note: The core agent runs out of the box with zero external packages).*

### Running the Agent

#### Interactive REPL Mode
```powershell
python agent.py
```

#### Single-Command Execution
```powershell
python agent.py "plan 120 minutes"
```

#### Structured JSON Output Mode
```powershell
python agent.py "plan 60 minutes" --json
```

#### Specifying Custom Storage File
```powershell
python agent.py "list tasks" --data my_custom_tasks.json
```

---

## 7. Example Inputs & Real Terminal Outputs

### Example 1: Adding a Task with Priority & Due Date
**Input**:
```powershell
python agent.py "add Practice SQL for 30 minutes priority medium due 2026-10-25"
```
**Output**:
```text
Task captured: Added 'Practice SQL' (30 minutes, medium priority, due: 2026-10-25).

Current task list:
1. [pending] Revise DBMS - 45 min, high priority
2. [pending] Practice SQL - 30 min, medium priority, due: 2026-10-25

Action/Observation Trace:
[
  {
    "tool": "add_task",
    "observation": "Added 'Practice SQL' (30 minutes, medium priority, due: 2026-10-25)."
  },
  {
    "tool": "list_tasks",
    "observation": "1. [pending] Revise DBMS - 45 min, high priority\n2. [pending] Practice SQL - 30 min, medium priority, due: 2026-10-25"
  }
]
```

### Example 2: Generating a Bounded Study Plan
**Input**:
```powershell
python agent.py "plan 60 minutes"
```
**Output**:
```text
Study plan for 60 minutes:
- 00-45 min: Revise DBMS (high priority)

Total planned: 45/60 minutes.

Action/Observation Trace:
[
  {
    "tool": "make_plan",
    "observation": "[{'task': 'Revise DBMS', 'minutes': 45, 'priority': 'high'}]"
  }
]
```

### Example 3: Completing a Task by Index
**Input**:
```powershell
python agent.py "complete 1"
```
**Output**:
```text
Marked task #1 'Revise DBMS' as done.

Current task list:
1. [done] Revise DBMS - 45 min, high priority
2. [pending] Practice SQL - 30 min, medium priority, due: 2026-10-25

Action/Observation Trace:
[
  {
    "tool": "complete_task",
    "observation": "Marked task #1 'Revise DBMS' as done."
  },
  {
    "tool": "list_tasks",
    "observation": "1. [done] Revise DBMS - 45 min, high priority\n2. [pending] Practice SQL - 30 min, medium priority, due: 2026-10-25"
  }
]
```

### Example 4: Input Validation Rejection
**Input**:
```powershell
python agent.py "add Practice SQL for -10 minutes"
```
**Output**:
```text
Error: Task duration must be a positive integer greater than 0 minutes, got -10.

Action/Observation Trace:
[]
```

---

## 8. Explanation of the Plan → Act → Observe Cycle

The agent follows an explicit four-phase execution cycle for every student request:

```
+---------------+     +--------------+     +-----------------+     +--------------------+
|  1. PLAN      | --> |  2. ACT      | --> |  3. OBSERVE     | --> |  4. EVALUATE       |
| Interpret &   |     | Execute Tool |     | Capture Output  |     | Update State, List |
| Validate Goal |     | Function     |     | in Trace Logger |     | & Return Response  |
+---------------+     +--------------+     +-----------------+     +--------------------+
```

1. **Plan**: The agent intercepts the user's string, identifies intent using deterministic regular expressions, and validates all parameters (e.g. ensuring `minutes > 0` and priority is within `{high, medium, low}`).
2. **Act**: The agent dispatches execution to the corresponding tool in `StudyTools` via the `_act` method.
3. **Observe**: The tool's output is recorded as an observation record into `agent.trace`.
4. **Evaluate & Respond**: For state mutations (adding or completing tasks), the agent evaluates the result and automatically invokes `list_tasks` to inspect updated state. The complete action trace and final response are then serialized for the user.

---

## 9. Testing Instructions & Actual Results

### Running All Automated Tests
The test suite uses Python's built-in `unittest` module. Tests use temporary directories (`tempfile.TemporaryDirectory`) so your runtime and sample tasks in `data/tasks.json` are never modified.

Run the following command in PowerShell:
```powershell
python -m unittest discover -s tests -v
```

### Actual Test Results
```text
test_cli_execution_with_json_flag (test_agent.TestCliIntegration.test_cli_execution_with_json_flag)
Verify running agent.py from command line with --json produces schema-valid output. ... ok
test_add_command_parsing (test_agent.TestStudyAgent.test_add_command_parsing)
Verify natural language 'add' command parsing with various formats. ... ok
test_complete_action_observation_trace (test_agent.TestStudyAgent.test_complete_action_observation_trace)
Verify complete trace captures all executed tools and observations. ... ok
test_complete_empty_identifier_handled (test_agent.TestStudyAgent.test_complete_empty_identifier_handled)
Verify completing without identifier gives helpful instruction. ... ok
test_complete_supported_command_variations (test_agent.TestStudyAgent.test_complete_supported_command_variations)
Verify multiple phrasing variations for completing tasks work reliably. ... ok
test_plan_rejects_zero_or_negative_minutes (test_agent.TestStudyAgent.test_plan_rejects_zero_or_negative_minutes)
Verify planning goal rejects zero or negative available study time. ... ok
test_plan_when_no_tasks_fit (test_agent.TestStudyAgent.test_plan_when_no_tasks_fit)
Verify friendly notification when no pending tasks fit into available time. ... ok
test_reject_invalid_due_date_in_goal (test_agent.TestStudyAgent.test_reject_invalid_due_date_in_goal)
Verify agent rejects invalid date formats in user input. ... ok
test_reject_invalid_priority_in_goal (test_agent.TestStudyAgent.test_reject_invalid_priority_in_goal)
Verify agent rejects invalid priority in user input. ... ok
test_reject_zero_and_negative_duration_in_goal (test_agent.TestStudyAgent.test_reject_zero_and_negative_duration_in_goal)
Verify agent rejects zero or negative durations from user input. ... ok
test_schema_compliance_of_structured_output (test_agent.TestStudyAgent.test_schema_compliance_of_structured_output)
Verify that agent.execute() produces structured output matching schema.json. ... ok
test_schema_validator_rejects_invalid_data (test_agent.TestStudyAgent.test_schema_validator_rejects_invalid_data)
Verify schema validator detects missing fields and constraint violations. ... ok
test_trace_resets_between_requests (test_agent.TestStudyAgent.test_trace_resets_between_requests)
Verify that agent.trace is isolated per request and resets cleanly. ... ok
test_unknown_and_empty_goal_handling (test_agent.TestStudyAgent.test_unknown_and_empty_goal_handling)
Verify agent returns helpful guidance for empty or unrecognized inputs. ... ok
test_add_valid_task (test_agent.TestStudyTools.test_add_valid_task)
Verify adding a task saves and reports correctly. ... ok
test_complete_already_done_task (test_agent.TestStudyTools.test_complete_already_done_task)
Verify notification when completing an already completed task. ... ok
test_complete_nonexistent_task (test_agent.TestStudyTools.test_complete_nonexistent_task)
Verify graceful error reporting when completing non-existent task. ... ok
test_complete_task_by_index (test_agent.TestStudyTools.test_complete_task_by_index)
Verify completing task using 1-based numerical index. ... ok
test_complete_task_by_title_fragment (test_agent.TestStudyTools.test_complete_task_by_title_fragment)
Verify completing task using a case-insensitive title fragment. ... ok
test_handle_corrupted_json_gracefully (test_agent.TestStudyTools.test_handle_corrupted_json_gracefully)
Verify tools handle corrupted JSON on disk without unhandled crash. ... ok
test_list_empty_tasks (test_agent.TestStudyTools.test_list_empty_tasks)
Verify listing behavior when store has no tasks. ... ok
test_make_plan_respects_time_limit (test_agent.TestStudyTools.test_make_plan_respects_time_limit)
Verify study plan does not exceed available minutes. ... ok
test_persistence_save_and_reload (test_agent.TestStudyTools.test_persistence_save_and_reload)
Verify tasks persist to disk and reload accurately. ... ok
test_prioritizes_due_dates_within_same_priority (test_agent.TestStudyTools.test_prioritizes_due_dates_within_same_priority)
Verify tasks with earlier deadlines rank first within the same priority. ... ok
test_prioritizes_tasks_correctly (test_agent.TestStudyTools.test_prioritizes_tasks_correctly)
Verify prioritization ranks high before medium before low. ... ok
test_reject_empty_title (test_agent.TestTaskModel.test_reject_empty_title)
Verify that empty or whitespace titles raise ValueError. ... ok
test_reject_invalid_due_date_format (test_agent.TestTaskModel.test_reject_invalid_due_date_format)
Verify that invalid due date strings raise ValueError. ... ok
test_reject_invalid_priority (test_agent.TestTaskModel.test_reject_invalid_priority)
Verify that non-whitelisted priorities raise ValueError. ... ok
test_reject_zero_and_negative_duration (test_agent.TestTaskModel.test_reject_zero_and_negative_duration)
Verify that zero or negative durations raise ValueError. ... ok
test_valid_task_creation (test_agent.TestTaskModel.test_valid_task_creation)
Verify normal task creation with valid inputs. ... ok

----------------------------------------------------------------------
Ran 30 tests in 0.452s

OK
```

---

## 10. Limitations & Future Improvements

### Current Limitations
- **Rule-Based Intent Parsing**: The goal interpreter uses regular expressions and string matching rather than an LLM. While deterministic and 100% offline, it cannot infer ambiguous phrases outside supported patterns.
- **Single-Day Session Planning**: The planner greedy-packs tasks for a single available time block rather than multi-day calendar scheduling.
- **Local JSON Storage**: Suitable for single-user desktop assignment demos; not concurrent across multiple processes.

### Future Improvements
- **LLM Intent Routing**: Replace regex parsing with a local small language model (e.g., Ollama / LLaMA-3) or an API-based LLM.
- **Google Calendar / ICS Sync**: Export generated study schedules directly into calendar applications.
- **Pomodoro Break Scheduling**: Automatically insert 5-minute restorative breaks between study intervals.

---

## 11. Instructions for Manually Uploading to GitHub

Follow these steps to upload the clean project files manually or via Git without committing keys or runtime junk.

### Project File Structure to Upload
```text
student-task-agent/
├── .gitignore
├── README.md
├── agent.py
├── architecture.md
├── requirements.txt
├── schema.json
├── data/
│   ├── sample_tasks.json
│   └── tasks.json
└── tests/
    ├── __init__.py
    └── test_agent.py

4. Type a commit message: `Initial submission for Agentic AI Study Assistant`.
5. Click **Commit changes**.

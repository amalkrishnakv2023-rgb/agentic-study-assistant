"""Agentic Study Assistant.

A lightweight, rule-based student task-planning agent developed for a college
Agentic AI assignment.

The agent demonstrates an explicit, observable Plan -> Act -> Observe -> Evaluate
cycle. Tools are implemented as modular Python functions with local JSON persistence,
requiring no API keys, cloud services, or external models.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable


# ============================================================================
# 1. Data Model
# ============================================================================

VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"pending", "done"}
PRIORITY_WEIGHTS = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    """Represents a student study task."""
    title: str
    minutes: int
    priority: str = "medium"
    status: str = "pending"
    due_date: str | None = None

    def __post_init__(self) -> None:
        """Validate task fields upon initialization."""
        self.title = str(self.title).strip()
        if not self.title:
            raise ValueError("Task title cannot be empty.")

        try:
            self.minutes = int(self.minutes)
        except (ValueError, TypeError):
            raise ValueError(f"Task duration must be a valid integer, got {self.minutes!r}.")

        if self.minutes <= 0:
            raise ValueError(f"Task duration must be a positive integer greater than 0, got {self.minutes}.")

        self.priority = str(self.priority).lower().strip()
        if self.priority not in VALID_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{self.priority}'. Allowed priorities: {', '.join(sorted(VALID_PRIORITIES))}."
            )

        self.status = str(self.status).lower().strip()
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. Allowed statuses: {', '.join(sorted(VALID_STATUSES))}."
            )

        if self.due_date is not None:
            self.due_date = str(self.due_date).strip()
            if not self.due_date:
                self.due_date = None
            else:
                try:
                    # Validates ISO 8601 YYYY-MM-DD
                    date.fromisoformat(self.due_date)
                except ValueError:
                    raise ValueError(
                        f"Invalid due date '{self.due_date}'. Expected format YYYY-MM-DD (e.g. 2026-10-25)."
                    )

    def to_dict(self) -> dict[str, Any]:
        """Convert task instance to dictionary representation."""
        return asdict(self)


# ============================================================================
# 2. Tool Layer (Action Execution & Persistence)
# ============================================================================

class StudyTools:
    """Action layer providing concrete study tools with local JSON persistence."""

    def __init__(self, store_path: Path):
        self.store_path = Path(store_path)
        self.tasks: list[Task] = []
        self.load_tasks()

    def load_tasks(self) -> str:
        """Load tasks from the JSON storage file, handling errors gracefully."""
        self.tasks = []
        if not self.store_path.exists():
            return f"Store file '{self.store_path}' does not exist yet. Initialized empty task list."

        try:
            content = self.store_path.read_text(encoding="utf-8").strip()
            if not content:
                return f"Store file '{self.store_path}' is empty. Initialized empty task list."

            raw_data = json.loads(content)
            if not isinstance(raw_data, list):
                return (
                    f"Warning: Store file '{self.store_path}' does not contain a JSON list. "
                    "Initialized empty task list."
                )

            valid_tasks: list[Task] = []
            for idx, item in enumerate(raw_data, start=1):
                if not isinstance(item, dict):
                    continue
                try:
                    task = Task(
                        title=item.get("title", ""),
                        minutes=item.get("minutes", 0),
                        priority=item.get("priority", "medium"),
                        status=item.get("status", "pending"),
                        due_date=item.get("due_date"),
                    )
                    valid_tasks.append(task)
                except ValueError as err:
                    # Skip corrupt records without crashing the whole application
                    continue

            self.tasks = valid_tasks
            return f"Successfully loaded {len(self.tasks)} task(s) from {self.store_path}."

        except json.JSONDecodeError as err:
            return f"Warning: Corrupted JSON in '{self.store_path}' ({err}). Initialized empty task list."
        except OSError as err:
            return f"Warning: Could not read '{self.store_path}' ({err}). Initialized empty task list."

    def save_tasks(self) -> str:
        """Persist current tasks to local JSON storage."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            serialized = json.dumps([t.to_dict() for t in self.tasks], indent=2)
            self.store_path.write_text(serialized, encoding="utf-8")
            return f"Saved {len(self.tasks)} task(s) to {self.store_path}."
        except OSError as err:
            return f"Error: Failed to save tasks to '{self.store_path}': {err}"

    def add_task(
        self,
        title: str,
        minutes: int,
        priority: str = "medium",
        due_date: str | None = None,
    ) -> str:
        """Add a new task with validation and persist it."""
        try:
            task = Task(title=title, minutes=minutes, priority=priority, due_date=due_date)
        except ValueError as err:
            return f"Error: {err}"

        self.tasks.append(task)
        save_msg = self.save_tasks()
        if save_msg.startswith("Error:"):
            return save_msg

        deadline_str = f", due: {task.due_date}" if task.due_date else ""
        return f"Added '{task.title}' ({task.minutes} minutes, {task.priority} priority{deadline_str})."

    def list_tasks(self) -> str:
        """Format and return all stored tasks."""
        if not self.tasks:
            return "No tasks are saved yet."

        lines = []
        for i, t in enumerate(self.tasks, start=1):
            due_str = f", due: {t.due_date}" if t.due_date else ""
            lines.append(
                f"{i}. [{t.status}] {t.title} - {t.minutes} min, {t.priority} priority{due_str}"
            )
        return "\n".join(lines)

    def make_plan(self, available_minutes: int) -> list[dict[str, Any]]:
        """Schedule pending tasks within available time, prioritized by importance and deadlines."""
        if available_minutes <= 0:
            return []

        # Filter only pending tasks
        pending = [t for t in self.tasks if t.status == "pending"]

        # Prioritization heuristic:
        # 1. Priority level: high (0) > medium (1) > low (2)
        # 2. Due date: tasks with earlier deadlines first; tasks without deadline come after
        # 3. Duration: shorter tasks first as a tie-breaker
        def sort_key(t: Task) -> tuple[int, int, str, int]:
            priority_rank = PRIORITY_WEIGHTS.get(t.priority, 1)
            has_due = 0 if t.due_date else 1
            due_val = t.due_date if t.due_date else "9999-99-99"
            return (priority_rank, has_due, due_val, t.minutes)

        sorted_pending = sorted(pending, key=sort_key)

        left = available_minutes
        plan: list[dict[str, Any]] = []
        for task in sorted_pending:
            if task.minutes <= left:
                plan_item: dict[str, Any] = {
                    "task": task.title,
                    "minutes": task.minutes,
                    "priority": task.priority,
                }
                if task.due_date:
                    plan_item["due_date"] = task.due_date
                plan.append(plan_item)
                left -= task.minutes

        return plan

    def complete_task(self, identifier: str) -> str:
        """Mark a task as done by 1-based index or title fragment."""
        clean_id = identifier.strip()
        if not clean_id:
            return "Error: No task identifier provided."

        # Case 1: Match by 1-based index (e.g. "1", "2")
        if clean_id.isdigit():
            idx = int(clean_id)
            if 1 <= idx <= len(self.tasks):
                target_task = self.tasks[idx - 1]
                if target_task.status == "done":
                    return f"Task #{idx} '{target_task.title}' is already completed."
                target_task.status = "done"
                self.save_tasks()
                return f"Marked task #{idx} '{target_task.title}' as done."
            return (
                f"Task index #{idx} is out of range. "
                f"Currently there are {len(self.tasks)} saved task(s)."
            )

        # Case 2: Match by title substring (case-insensitive)
        lowered_id = clean_id.lower()
        matched_pending: Task | None = None
        matched_already_done: Task | None = None

        for task in self.tasks:
            if lowered_id in task.title.lower():
                if task.status == "pending" and matched_pending is None:
                    matched_pending = task
                elif task.status == "done" and matched_already_done is None:
                    matched_already_done = task

        if matched_pending is not None:
            matched_pending.status = "done"
            self.save_tasks()
            return f"Marked '{matched_pending.title}' as done."

        if matched_already_done is not None:
            return f"Task '{matched_already_done.title}' is already completed."

        return f"No pending task matched '{clean_id}'."


# ============================================================================
# 3. Agent Layer (Goal Interpreter, Action Selection, Trace & Lifecycle)
# ============================================================================

class StudyAgent:
    """Bounded, rule-based Agent following a Plan -> Act -> Observe -> Evaluate loop.

    Architectural stages:
    1. Plan: Interpret student goal, validate parameters, and select appropriate tool.
    2. Act: Execute chosen tool with parsed arguments.
    3. Observe: Capture execution result into structured trace.
    4. Evaluate & Respond: Construct user-facing response and structured schema output.
    """

    def __init__(self, tools: StudyTools):
        self.tools = tools
        # Holds the complete action/observation trace for the latest request
        self.trace: list[dict[str, str]] = []
        # Optional cumulative history across requests
        self.history: list[dict[str, Any]] = []

    def _act(self, tool_name: str, fn: Callable[..., Any], *args: Any) -> Any:
        """Execute a tool action and record its observable result in the trace."""
        observation = fn(*args)
        self.trace.append({
            "tool": tool_name,
            "observation": str(observation) if not isinstance(observation, str) else observation,
        })
        return observation

    # ------------------------------------------------------------------------
    # Natural Language Parsing Helpers
    # ------------------------------------------------------------------------

    def _parse_add_goal(self, text: str) -> tuple[str, int, str, str | None, str | None]:
        """Parse natural-language 'add' command.

        Returns (title, minutes, priority, due_date, error_message).
        Supported patterns:
          add <title> [for <minutes> [mins|minutes]] [priority <high|medium|low>] [due <YYYY-MM-DD>]
        Tokens can appear in any order after 'add'.
        """
        # Remove leading 'add'
        payload = re.sub(r"^add\s+", "", text, flags=re.I).strip()
        if not payload:
            return "", 0, "", None, "Please specify a task title. Example: add Revise OS for 45 minutes priority high"

        # 1. Extract duration if present
        minutes = 30
        min_match = re.search(r"(?:for\s+)?(-?\d+)\s*(?:minutes?|mins?|min)\b", payload, re.I)
        if min_match:
            try:
                raw_min = int(min_match.group(1))
                if raw_min <= 0:
                    return "", 0, "", None, (
                        f"Task duration must be a positive integer greater than 0 minutes, got {raw_min}."
                    )
                minutes = raw_min
            except ValueError:
                return "", 0, "", None, "Invalid minutes value."
            # Remove duration token from payload to isolate title
            payload = payload[:min_match.start()] + " " + payload[min_match.end():]

        # 2. Extract priority if present
        priority = "medium"
        prio_match = re.search(r"\bpriority\s+([a-zA-Z]+)\b", payload, re.I)
        if prio_match:
            extracted_prio = prio_match.group(1).lower()
            if extracted_prio not in VALID_PRIORITIES:
                return "", 0, "", None, (
                    f"Invalid priority '{extracted_prio}'. Allowed priorities: {', '.join(sorted(VALID_PRIORITIES))}."
                )
            priority = extracted_prio
            payload = payload[:prio_match.start()] + " " + payload[prio_match.end():]

        # 3. Extract due date if present (e.g. 'due 2026-10-25' or 'by 2026-10-25')
        due_date: str | None = None
        due_match = re.search(r"\b(?:due|by)\s+([0-9\-\/]+)\b", payload, re.I)
        if due_match:
            extracted_due = due_match.group(1).strip()
            try:
                # Normalize and validate ISO date
                valid_dt = date.fromisoformat(extracted_due)
                due_date = valid_dt.isoformat()
            except ValueError:
                return "", 0, "", None, (
                    f"Invalid due date '{extracted_due}'. Expected format YYYY-MM-DD (e.g. 2026-10-25)."
                )
            payload = payload[:due_match.start()] + " " + payload[due_match.end():]

        # Remaining text is the task title
        title = re.sub(r"\s+", " ", payload).strip()
        # Clean potential trailing punctuation or residual words
        title = re.sub(r"^[\"']|[\"']$", "", title).strip()

        if not title:
            return "", 0, "", None, "Please specify a task title. Example: add Revise OS for 45 minutes priority high"

        return title, minutes, priority, due_date, None

    def _parse_complete_goal(self, text: str) -> tuple[str, str | None]:
        """Extract task identifier from completion commands.

        Supported formats:
          - complete <id> / complete task <id>
          - done <id> / done task <id>
          - mark <id> as done / mark <id> as complete
        """
        raw = text.strip()
        # Strip prefixes
        cleaned = re.sub(
            r"^(?:mark\s+task\b|mark\b|complete\s+task\b|complete\b|done\s+task\b|done\b|finish\s+task\b|finish\b)\s*",
            "",
            raw,
            flags=re.I,
        ).strip()
        # Strip suffixes
        cleaned = re.sub(r"\s+as\s+(?:done|complete|completed)$", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"^[\"']|[\"']$", "", cleaned).strip()

        if not cleaned:
            return "", "Please specify which task to complete. Example: complete 1 or complete DBMS"
        return cleaned, None

    def _parse_plan_goal(self, text: str) -> tuple[int, str | None]:
        """Extract available minutes from planning goals."""
        match = re.search(r"(-?\d+)\s*(?:minutes?|mins?|min)?", text, re.I)
        if match:
            try:
                available = int(match.group(1))
                if available <= 0:
                    return 0, f"Available study time must be greater than 0 minutes, got {available}."
                return available, None
            except ValueError:
                return 120, None
        return 120, None

    # ------------------------------------------------------------------------
    # Execution Lifecycle
    # ------------------------------------------------------------------------

    def execute(self, goal: str) -> dict[str, Any]:
        """Execute the full Plan -> Act -> Observe -> Evaluate cycle for a goal.

        Resets and records a fresh trace for each request. Returns a structured
        result dictionary conforming strictly to schema.json.
        """
        # Always isolate trace per request
        self.trace = []
        raw_goal = goal.strip()
        lowered = raw_goal.lower()

        plan_items: list[dict[str, Any]] = []
        message: str = ""

        if not raw_goal:
            message = "Please enter a study goal. Example: 'plan 120 minutes' or 'add Revise OS for 45 minutes priority high'."
            result = self._format_result(raw_goal, message, plan_items)
            self.history.append(result)
            return result

        # --------------------------------------------------------------------
        # Intent 1: Add Task
        # --------------------------------------------------------------------
        if lowered.startswith("add ") or lowered == "add":
            title, minutes, priority, due_date, err = self._parse_add_goal(raw_goal)
            if err:
                message = f"Error: {err}"
            else:
                add_obs = self._act("add_task", self.tools.add_task, title, minutes, priority, due_date)
                list_obs = self._act("list_tasks", self.tools.list_tasks)
                message = f"Task captured: {add_obs}\n\nCurrent task list:\n{list_obs}"

        # --------------------------------------------------------------------
        # Intent 2: Complete Task
        # --------------------------------------------------------------------
        elif (
            lowered.startswith("complete")
            or lowered.startswith("done")
            or lowered.startswith("finish")
            or "mark " in lowered
            or " as done" in lowered
            or " as complete" in lowered
        ):
            target_id, err = self._parse_complete_goal(raw_goal)
            if err:
                message = f"Error: {err}"
            else:
                comp_obs = self._act("complete_task", self.tools.complete_task, target_id)
                list_obs = self._act("list_tasks", self.tools.list_tasks)
                message = f"{comp_obs}\n\nCurrent task list:\n{list_obs}"

        # --------------------------------------------------------------------
        # Intent 3: List / Show Tasks
        # --------------------------------------------------------------------
        elif any(word in lowered for word in ("list", "show", "status", "tasks")):
            list_obs = self._act("list_tasks", self.tools.list_tasks)
            message = f"Current task list:\n{list_obs}"

        # --------------------------------------------------------------------
        # Intent 4: Study Planning
        # --------------------------------------------------------------------
        elif any(word in lowered for word in ("plan", "study", "schedule")):
            available, err = self._parse_plan_goal(raw_goal)
            if err:
                message = f"Error: {err}"
            else:
                plan_items = self._act("make_plan", self.tools.make_plan, available)
                if not plan_items:
                    message = (
                        f"No pending tasks fit into {available} minutes.\n"
                        "Add tasks with: add <topic> for <minutes> minutes priority high|medium|low"
                    )
                else:
                    lines = [f"Study plan for {available} minutes:"]
                    cursor = 0
                    for item in plan_items:
                        start = cursor
                        cursor += item["minutes"]
                        due_note = f", due: {item['due_date']}" if "due_date" in item and item["due_date"] else ""
                        lines.append(
                            f"- {start:02d}-{cursor:02d} min: {item['task']} "
                            f"({item['priority']} priority{due_note})"
                        )
                    total_planned = cursor
                    lines.append(f"\nTotal planned: {total_planned}/{available} minutes.")
                    message = "\n".join(lines)

        # --------------------------------------------------------------------
        # Fallback: Guidance
        # --------------------------------------------------------------------
        else:
            message = (
                "I am a rule-based Study Planning Agent. I can:\n"
                "  1. Add a task:      add Revise DBMS for 45 minutes priority high due 2026-10-25\n"
                "  2. Plan a session:  plan 120 minutes\n"
                "  3. List all tasks:  list tasks\n"
                "  4. Complete a task: complete DBMS (or: complete 1 / mark DBMS as done)"
            )

        result = self._format_result(raw_goal, message, plan_items)
        self.history.append(result)
        return result

    def _format_result(
        self, goal: str, message: str, plan_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Construct a structured dictionary matching schema.json."""
        return {
            "goal": goal,
            "message": message,
            "plan": plan_items,
            "tool_trace": list(self.trace),
            "tasks": [t.to_dict() for t in self.tools.tasks],
        }

    def run(self, goal: str) -> str:
        """Run the agent for a goal and return human-readable text."""
        result = self.execute(goal)
        return str(result["message"])


# ============================================================================
# 4. Schema Validator Helper
# ============================================================================

def validate_agent_output(
    data: dict[str, Any], schema_path: Path | None = None
) -> tuple[bool, str | None]:
    """Validate a structured agent output dictionary against schema.json.

    Uses `jsonschema` if installed, or performs strict built-in validation
    when running dependency-free.
    """
    # 1. Try formal validation using jsonschema if available
    try:
        import jsonschema  # type: ignore

        resolved_schema_path = (
            Path(schema_path) if schema_path else Path(__file__).parent / "schema.json"
        )
        if resolved_schema_path.exists():
            schema = json.loads(resolved_schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=data, schema=schema)
            return True, None
    except ImportError:
        pass  # Fall back to built-in validation
    except Exception as err:
        return False, str(err)

    # 2. Built-in structural validation
    if not isinstance(data, dict):
        return False, "Data must be a dictionary."

    required_keys = {"goal", "plan", "tool_trace"}
    missing = required_keys - set(data.keys())
    if missing:
        return False, f"Missing required schema fields: {missing}"

    if not isinstance(data["goal"], str):
        return False, "Field 'goal' must be a string."

    if not isinstance(data["plan"], list):
        return False, "Field 'plan' must be a list."

    for item in data["plan"]:
        if not isinstance(item, dict):
            return False, "Each item in 'plan' must be a dictionary."
        if not all(k in item for k in ("task", "minutes", "priority")):
            return False, "Each plan item requires 'task', 'minutes', and 'priority'."
        if not isinstance(item["minutes"], int) or item["minutes"] < 1:
            return False, "Plan item 'minutes' must be an integer >= 1."
        if item["priority"] not in VALID_PRIORITIES:
            return False, f"Plan item 'priority' must be one of {VALID_PRIORITIES}."

    if not isinstance(data["tool_trace"], list):
        return False, "Field 'tool_trace' must be a list."

    for trace_entry in data["tool_trace"]:
        if not isinstance(trace_entry, dict):
            return False, "Each trace entry must be a dictionary."
        if not all(k in trace_entry for k in ("tool", "observation")):
            return False, "Each trace entry requires 'tool' and 'observation'."

    if "tasks" in data:
        if not isinstance(data["tasks"], list):
            return False, "Field 'tasks' must be a list."
        for t in data["tasks"]:
            if not isinstance(t, dict):
                return False, "Each task must be a dictionary."
            if not all(k in t for k in ("title", "minutes", "priority", "status")):
                return False, "Task requires 'title', 'minutes', 'priority', and 'status'."
            if not isinstance(t["minutes"], int) or t["minutes"] < 1:
                return False, "Task 'minutes' must be an integer >= 1."
            if t["priority"] not in VALID_PRIORITIES:
                return False, f"Task 'priority' must be one of {VALID_PRIORITIES}."
            if t["status"] not in VALID_STATUSES:
                return False, f"Task 'status' must be one of {VALID_STATUSES}."

    return True, None


# ============================================================================
# 5. CLI Entrypoint
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentic Study Assistant — Rule-Based Plan-Act-Observe Agent"
    )
    parser.add_argument("goal", nargs="*", help="Goal, e.g. 'plan 120 minutes'")
    parser.add_argument(
        "--data", default="data/tasks.json", help="Path to task storage JSON file"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output schema-compliant structured JSON"
    )
    args = parser.parse_args()

    tools = StudyTools(Path(args.data))
    agent = StudyAgent(tools)

    # Mode 1: Single command-line invocation
    if args.goal:
        goal_text = " ".join(args.goal)
        response = agent.execute(goal_text)
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            print(response["message"])
            print("\nAction/Observation Trace:")
            print(json.dumps(agent.trace, indent=2))
        return

    # Mode 2: Interactive REPL loop
    print("=" * 60)
    print(" Agentic Study Assistant (Rule-Based Demo)")
    print(" Demonstrating Plan -> Act -> Observe -> Evaluate loop")
    print(" Type 'help' for examples or 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit"}:
            print("Session ended. Happy studying!")
            break

        response = agent.execute(user_input)
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            print(f"\nAgent:\n{response['message']}")
            print("\nAction/Observation Trace:")
            print(json.dumps(agent.trace, indent=2))


if __name__ == "__main__":
    main()

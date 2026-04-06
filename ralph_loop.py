#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Autonomous Task Completion
================================================
The Ralph Wiggum pattern keeps the AI Employee working autonomously
until a task is complete. It intercepts exit attempts and re-injects
prompts with context until the task is done.

Usage:
    python ralph_loop.py --task TASK_ID --max-iterations 10

Or via orchestrator:
    python orchestrator.py ralph-loop --task TASK_001

Architecture:
    Task Created → Process Step → Check Progress → Complete?
                              ↓ NO
           ↓ YES ← Re-inject Prompt ←┘
    Done!
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any

logger = logging.getLogger('RalphLoop')


class TaskState:
    """Represents the state of a task being processed by Ralph Loop"""

    def __init__(self, task_id: str, task_file: Path, prompt: str,
                 max_iterations: int = 10, completion_promise: str = "TASK_COMPLETE"):
        self.task_id = task_id
        self.task_file = task_file
        self.prompt = prompt
        self.max_iterations = max_iterations
        self.completion_promise = completion_promise
        self.iteration = 0
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.status = "in_progress"  # in_progress, completed, failed, max_iterations_reached
        self.history: List[Dict] = []
        self.context: Dict[str, Any] = {}

    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization"""
        return {
            "task_id": self.task_id,
            "task_file": str(self.task_file),
            "prompt": self.prompt,
            "max_iterations": self.max_iterations,
            "completion_promise": self.completion_promise,
            "iteration": self.iteration,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "status": self.status,
            "history": self.history,
            "context": self.context
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TaskState':
        """Create TaskState from dictionary"""
        state = cls(
            task_id=data["task_id"],
            task_file=Path(data["task_file"]),
            prompt=data["prompt"],
            max_iterations=data.get("max_iterations", 10),
            completion_promise=data.get("completion_promise", "TASK_COMPLETE")
        )
        state.iteration = data.get("iteration", 0)
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.last_updated = datetime.fromisoformat(data["last_updated"])
        state.status = data.get("status", "in_progress")
        state.history = data.get("history", [])
        state.context = data.get("context", {})
        return state

    def record_action(self, action: str, result: str, metadata: dict = None):
        """Record an action in the history"""
        self.history.append({
            "iteration": self.iteration,
            "action": action,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now()

    def increment_iteration(self):
        """Increment the iteration counter"""
        self.iteration += 1
        self.last_updated = datetime.now()


class RalphLoop:
    """
    The Ralph Wiggum Loop - Keeps AI working until task is complete

    This class manages the lifecycle of autonomous task processing:
    1. Creates state files in In_Progress
    2. Monitors task completion (file moved to Done)
    3. Re-injects prompts with context when incomplete
    4. Enforces max iteration limits for safety
    """

    def __init__(self, vault_path: Path, max_iterations: int = 10,
                 completion_promise: str = "TASK_COMPLETE",
                 action_callback: Optional[Callable] = None):
        """
        Initialize Ralph Loop

        Args:
            vault_path: Path to the AI Employee Vault
            max_iterations: Maximum iterations before forcing completion
            completion_promise: String that signals completion in output
            action_callback: Optional callback for executing actions
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.in_progress = self.vault_path / "In_Progress"
        self.done = self.vault_path / "Done"
        self.plans = self.vault_path / "Plans"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.approved = self.vault_path / "Approved"

        self.max_iterations = max_iterations
        self.completion_promise = completion_promise
        self.action_callback = action_callback

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        for folder in [self.needs_action, self.in_progress, self.done,
                       self.plans, self.pending_approval, self.approved]:
            folder.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ready: {folder}")

    def create_state(self, task_file: Path, prompt: str = None) -> TaskState:
        """
        Create a new task state for Ralph Loop processing

        Args:
            task_file: Path to the task file in Needs_Action
            prompt: Optional custom prompt (default: task content)

        Returns:
            TaskState object
        """
        task_id = task_file.stem

        # Use task content as default prompt if not provided
        if prompt is None:
            try:
                prompt = task_file.read_text(encoding='utf-8')
            except Exception as e:
                prompt = f"Process task: {task_id}"
                logger.warning(f"Could not read task file: {e}")

        state = TaskState(
            task_id=task_id,
            task_file=task_file,
            prompt=prompt,
            max_iterations=self.max_iterations,
            completion_promise=self.completion_promise
        )

        # Save state file
        self._save_state(state)

        # Move task from Needs_Action to In_Progress
        self._claim_task(task_file)

        logger.info(f"Created Ralph Loop state for task: {task_id}")
        return state

    def _save_state(self, state: TaskState):
        """Save state to JSON file"""
        state_file = self.in_progress / f"ralph_state_{state.task_id}.json"
        state_file.write_text(json.dumps(state.to_dict(), indent=2), encoding='utf-8')

    def load_state(self, task_id: str) -> Optional[TaskState]:
        """Load state from JSON file"""
        state_file = self.in_progress / f"ralph_state_{task_id}.json"
        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text(encoding='utf-8'))
            return TaskState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state for {task_id}: {e}")
            return None

    def _claim_task(self, task_file: Path):
        """Move task from Needs_Action to In_Progress"""
        if task_file.exists():
            in_progress_file = self.in_progress / task_file.name
            task_file.rename(in_progress_file)
            logger.info(f"Claimed task: {task_file.name} → In_Progress/")

    def check_completion(self, task_id: str) -> bool:
        """
        Check if task is complete

        Task is considered complete if:
        1. File exists in /Done folder
        2. .complete marker file exists in /In_Progress
        3. Output contains TASK_COMPLETE promise

        Args:
            task_id: The task ID to check

        Returns:
            True if complete, False otherwise
        """
        # Check for file in Done folder (exact match or with timestamp)
        done_marker = self.done / f"{task_id}.md"
        done_marker_alt = self.done / f"DONE_{task_id}.md"

        if done_marker.exists() or done_marker_alt.exists():
            logger.info(f"Task {task_id} complete: Found in /Done")
            return True

        # Check for completion marker in In_Progress
        complete_marker = self.in_progress / f"{task_id}.complete"
        if complete_marker.exists():
            logger.info(f"Task {task_id} complete: Marker file found")
            return True

        # Check if task file was moved elsewhere (like /Approved or /Rejected)
        task_file = self.in_progress / f"{task_id}.md"
        if not task_file.exists():
            # Check if it exists elsewhere
            for folder in [self.pending_approval, self.approved]:
                if (folder / f"{task_id}.md").exists():
                    logger.info(f"Task {task_id} moved to: {folder.name}")
                    return True

        return False

    def should_continue(self, task_id: str) -> bool:
        """
        Determine if Ralph Loop should continue processing

        Returns False if:
        - Task is complete
        - Max iterations reached
        - Task failed

        Args:
            task_id: The task ID to check

        Returns:
            True to continue, False to stop
        """
        state = self.load_state(task_id)
        if not state:
            logger.warning(f"No state found for task: {task_id}")
            return False

        # Check completion
        if self.check_completion(task_id):
            state.status = "completed"
            self._save_state(state)
            self._cleanup_state(task_id)
            return False

        # Check max iterations
        if state.iteration >= self.max_iterations:
            logger.warning(f"Max iterations ({self.max_iterations}) reached for task: {task_id}")
            state.status = "max_iterations_reached"
            self._save_state(state)
            return False

        # Check if task is in failed state
        if state.status == "failed":
            logger.error(f"Task {task_id} in failed state")
            return False

        return True

    def get_reinjection_prompt(self, task_id: str) -> str:
        """
        Generate the re-injection prompt for the next iteration

        This prompt is displayed when Claude tries to exit but the
        task is not yet complete.

        Args:
            task_id: The task ID

        Returns:
            The re-injection prompt string
        """
        state = self.load_state(task_id)
        if not state:
            return f"Continue working on task: {task_id}"

        state.increment_iteration()

        # Build context from history (last 5 actions)
        history_context = ""
        if state.history:
            history_context = "\nPrevious actions:\n"
            for h in state.history[-5:]:
                history_context += f"  - Iteration {h['iteration']}: {h['action']} - {h['result']}\n"

        # Determine what to focus on based on iteration
        if state.iteration == 1:
            focus = "Start by analyzing the task and creating a plan."
        elif state.iteration < state.max_iterations // 2:
            focus = "Continue executing your plan. Record progress."
        else:
            focus = "Task should be nearing completion. Finalize and move to /Done."

        reinjection = f"""
╔══════════════════════════════════════════════════════════════════╗
║           RALPH WIGGUM LOOP - TASK CONTINUATION                  ║
╚══════════════════════════════════════════════════════════════════╝

Task ID: {task_id}
Iteration: {state.iteration}/{state.max_iterations}
Status: IN PROGRESS

{focus}

Original Task:
{state.prompt[:500]}{'...' if len(state.prompt) > 500 else ''}
{history_context}
Rules:
1. Work on ONE step at a time
2. Update the task file with progress
3. When COMPLETE, move file to /Done folder
4. Output "{self.completion_promise}" when finished

Continue working now:
"""

        self._save_state(state)
        return reinjection

    def record_action(self, task_id: str, action: str, result: str, metadata: dict = None):
        """Record an action taken during processing"""
        state = self.load_state(task_id)
        if state:
            state.record_action(action, result, metadata)
            self._save_state(state)

    def mark_complete(self, task_id: str, result_summary: str = ""):
        """
        Mark a task as complete

        Moves the task file to /Done and cleans up state
        """
        state = self.load_state(task_id)
        if not state:
            logger.warning(f"Cannot mark complete: No state for {task_id}")
            return False

        # Update status
        state.status = "completed"
        state.record_action("mark_complete", "Task marked as complete", {"summary": result_summary})
        self._save_state(state)

        # Move task file to Done
        task_file = self.in_progress / f"{task_id}.md"
        if task_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            done_file = self.done / f"DONE_{task_id}_{timestamp}.md"
            task_file.rename(done_file)
            logger.info(f"Moved task to Done: {done_file.name}")

        # Cleanup state file
        self._cleanup_state(task_id)

        return True

    def _cleanup_state(self, task_id: str):
        """Remove state file after completion"""
        state_file = self.in_progress / f"ralph_state_{task_id}.json"
        if state_file.exists():
            state_file.unlink()
            logger.debug(f"Cleaned up state file: {state_file.name}")

    def get_active_tasks(self) -> List[str]:
        """Get list of all active task IDs"""
        tasks = []
        for state_file in self.in_progress.glob("ralph_state_*.json"):
            task_id = state_file.stem.replace("ralph_state_", "")
            tasks.append(task_id)
        return tasks

    def process_task(self, task_id: str, callback: Callable[[str, TaskState], bool]) -> bool:
        """
        Process a single task with Ralph Loop

        This is the main entry point for autonomous task processing.
        It will keep calling the callback until the task is complete.

        Args:
            task_id: The task ID to process
            callback: Function(task_id, state) -> bool (True if work was done)

        Returns:
            True if task completed successfully, False otherwise
        """
        logger.info(f"Starting Ralph Loop processing for task: {task_id}")

        iteration = 0
        while self.should_continue(task_id):
            iteration += 1
            logger.info(f"Ralph Loop iteration {iteration} for task: {task_id}")

            state = self.load_state(task_id)
            if not state:
                logger.error(f"State lost for task: {task_id}")
                return False

            # Call the callback to do work
            try:
                work_done = callback(task_id, state)
                if not work_done:
                    logger.warning(f"No work done in iteration {iteration}")
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}")
                self.record_action(task_id, "error", str(e))

            # Small delay to prevent tight loops
            time.sleep(0.5)

        # Check final status
        if self.check_completion(task_id):
            logger.info(f"Task {task_id} completed successfully")
            return True
        else:
            logger.warning(f"Task {task_id} did not complete")
            return False


class RalphStopHook:
    """
    Stop hook that intercepts Claude's exit and re-injects prompt

    This integrates with the orchestrator to provide the Ralph Loop behavior.
    When Claude tries to exit, this hook checks if there are active tasks
    and re-injects the continuation prompt if needed.
    """

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.in_progress = self.vault_path / "In_Progress"
        self.done = self.vault_path / "Done"
        self.loop = RalphLoop(vault_path)

    def on_stop(self, task_id: str = None) -> tuple[bool, str]:
        """
        Called when Claude tries to exit

        Args:
            task_id: Optional specific task ID to check

        Returns:
            (should_exit, message): Whether to allow exit and message to show
        """
        # Find active state files
        if task_id:
            state = self.loop.load_state(task_id)
            if state and state.status == "in_progress":
                if self.loop.check_completion(task_id):
                    return True, f"✅ Task {task_id} complete. Exiting."
                else:
                    prompt = self.loop.get_reinjection_prompt(task_id)
                    return False, prompt
        else:
            # Check all active tasks
            active_tasks = self.loop.get_active_tasks()
            if not active_tasks:
                return True, "No active tasks. Exiting."

            # Check each active task
            incomplete_tasks = []
            for tid in active_tasks:
                if not self.loop.check_completion(tid):
                    incomplete_tasks.append(tid)

            if not incomplete_tasks:
                return True, "✅ All tasks complete. Exiting."

            # Re-inject for the first incomplete task
            prompt = self.loop.get_reinjection_prompt(incomplete_tasks[0])
            return False, f"⏳ {len(incomplete_tasks)} task(s) incomplete. Continuing...\n{prompt}"

        return True, "Exiting."


def create_test_task(vault_path: Path, task_name: str = "test_task") -> Path:
    """Create a test task in Needs_Action for Ralph Loop testing"""
    needs_action = Path(vault_path) / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)

    task_file = needs_action / f"{task_name}.md"
    content = f"""---
type: ralph_test
created: {datetime.now().isoformat()}
priority: medium
---

# Test Task for Ralph Loop

This is a test task to verify the Ralph Wiggum Loop is working.

## Steps to Complete:
1. Read this file
2. Create a plan in /Plans/{task_name}_plan.md
3. Execute the plan
4. Move this file to /Done when complete

## Completion Criteria
- Plan file exists
- Task is understood
"""
    task_file.write_text(content, encoding='utf-8')
    return task_file


def demo_ralph_loop():
    """Demonstrate Ralph Loop functionality"""
    print("="*60)
    print("RALPH WIGGUM LOOP - Demo")
    print("="*60)

    # Setup
    vault_path = Path("./AI_Employee_Vault")
    vault_path.mkdir(exist_ok=True)

    # Create test task
    task_file = create_test_task(vault_path, "demo_task_001")
    print(f"\n✅ Created test task: {task_file}")

    # Initialize Ralph Loop
    ralph = RalphLoop(vault_path, max_iterations=5)
    print("✅ Ralph Loop initialized")

    # Create state
    state = ralph.create_state(task_file)
    print(f"✅ Created state for task: {state.task_id}")

    # Simulate processing iterations
    for i in range(3):
        print(f"\n--- Iteration {i+1} ---")

        # Check if should continue
        if not ralph.should_continue(state.task_id):
            print("Task should not continue")
            break

        # Simulate some work
        ralph.record_action(state.task_id, f"step_{i+1}", f"Completed step {i+1}")
        print(f"✅ Recorded action: step_{i+1}")

        # Show reinjection prompt
        if i < 2:  # Don't show on last iteration
            prompt = ralph.get_reinjection_prompt(state.task_id)
            print(f"\nPrompt preview: {prompt[:200]}...")

    # Mark complete
    ralph.mark_complete(state.task_id, "Demo completed successfully")
    print(f"\n✅ Task marked complete")

    # Verify
    print(f"\n--- Verification ---")
    print(f"Active tasks: {ralph.get_active_tasks()}")
    print(f"Task in Done: {(vault_path / 'Done' / 'DONE_demo_task_001_').exists() or any('demo_task_001' in f.name for f in (vault_path / 'Done').glob('*'))}")

    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ralph Wiggum Loop")
    parser.add_argument("command", choices=["demo", "status", "test"], help="Command to run")
    parser.add_argument("--vault", default="./AI_Employee_Vault", help="Vault path")
    parser.add_argument("--task", help="Task ID to check")

    args = parser.parse_args()

    if args.command == "demo":
        demo_ralph_loop()
    elif args.command == "status":
        ralph = RalphLoop(args.vault)
        active = ralph.get_active_tasks()
        print(f"Active tasks: {len(active)}")
        for tid in active:
            print(f"  - {tid}")
    elif args.command == "test":
        print("Running Ralph Loop tests...")
        demo_ralph_loop()

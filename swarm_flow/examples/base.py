import asyncio
import sys

sys.path.append("..")

from modules.workflow import WorkflowExecutor

debug = True

# Multi-round dialogue example
if __name__ == "__main__":
    # Load workflow configuration
    with open("../data/base.yaml", "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Create a workflow executor
    executor = WorkflowExecutor(yaml_content=yaml_content, debug=debug)

    while True:
        # Execute workflow
        user_input = input("\nUser: ")
        output = asyncio.run(executor.run(user_input))
        print(f"Bot: {output}")

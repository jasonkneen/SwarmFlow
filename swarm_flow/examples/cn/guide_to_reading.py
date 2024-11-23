import asyncio
import sys

sys.path.append("../..")

from modules.workflow import WorkflowExecutor

debug = False

def print_status(message, type="info"):
    if not debug:
        print(message)

# Single round dialogue example
if __name__ == "__main__":
    # Load workflow configuration
    with open("../../data/cn/guide_to_reading.yaml", "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Load article content
    with open("guide_to_reading.txt", "r", encoding="utf-8") as f:
        article_content = f.read()

    print(f"Article content:\n```\n{article_content}\n```\n")

    # Create and run a workflow executor
    executor = WorkflowExecutor(yaml_content=yaml_content, debug=debug, status_callback=print_status)
    output = asyncio.run(executor.run(article_content))

    # Output the final result
    print("\n" + ("=" * 40) + "\n")
    print(output)

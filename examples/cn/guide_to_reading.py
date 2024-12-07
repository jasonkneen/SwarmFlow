import asyncio
import sys

sys.path.append("../..")

from swarm_flow.workflow import WorkflowExecutor

debug = False

workflow_config = "../../data/workflows/cn/guide_to_reading.yaml"
article = "guide_to_reading.txt"

def print_status(message, type="info"):
    if not debug:
        print(message)

# Single round dialogue example
if __name__ == "__main__":
    # Load workflow configuration
    with open(workflow_config, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Load article content
    with open(article, "r", encoding="utf-8") as f:
        article_content = f.read()

    print(f"Article content:\n```\n{article_content}\n```\n")

    # Create and run a workflow executor
    workflow_executor = WorkflowExecutor(yaml_content=yaml_content, debug=debug, status_callback=print_status)
    output = asyncio.run(workflow_executor.run(article_content))

    # Output the final result
    print("\n" + ("=" * 40) + "\n")
    print(output)

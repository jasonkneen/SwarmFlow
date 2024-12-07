import asyncio
import sys

sys.path.append("../..")

from swarm_flow.workflow import WorkflowExecutor

debug = False
stream_output = False

workflow_config = "../../data/workflows/cn/basic.yaml"

def status_callback(message, type="info"):
    pass

def stream_callback(chunk):
    if "content" in chunk and chunk["content"] is not None:
        print(chunk["content"].replace("\n\n", "\n"), end="", flush=True)

    if "delim" in chunk and chunk["delim"] == "end":
        print()  # End of response message


# Multi-round dialogue example
if __name__ == "__main__":
    # Load workflow configuration
    with open(workflow_config, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Create a workflow executor
    workflow_executor = WorkflowExecutor(
        yaml_content=yaml_content,
        stream=stream_output,
        debug=debug,
        status_callback=status_callback,
        stream_callback=stream_callback,
    )

    while True:
        # Execute workflow
        user_input = input("\nUser: ")
        print("Bot: ", end="")
        output = asyncio.run(workflow_executor.run(user_input))
        if debug or (not stream_output):
            print(f"{output}")

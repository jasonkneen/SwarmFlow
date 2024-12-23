import asyncio
import os

import yaml
import shutil
import sys

root_path = "../.."
sys.path.append(root_path)

from swarm_flow.workflow import WorkflowExecutor
from swarm_flow.rag.rag_simple import RAGSimple
from swarm_flow.config import rag_settings

debug = False
stream_output = True
rebuild_kb = True  # If the embedded model is changed, the vector database must be rebuilt.

workflow_config = f"{root_path}/data/workflows/cn/rag.yaml"
kb_document = f"{root_path}/data/knowledge_bases/documents/example_cn.txt"
kb_path = f"{root_path}/data/knowledge_bases/vector_stores/example_cn"

def status_callback(message, type="info"):
    pass

def stream_callback(chunk):
    if "content" in chunk and chunk["content"] is not None:
        print(chunk["content"].replace("\n\n", "\n"), end="", flush=True)

    if "delim" in chunk and chunk["delim"] == "end":
        print()  # End of response message


# RAG example
if __name__ == "__main__":
    # Load workflow configuration
    with open(workflow_config, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    if rebuild_kb and os.path.exists(kb_path):
        shutil.rmtree(kb_path)

    # Extract RAG settings
    rag_provider = ""
    workflow_config = yaml.safe_load(yaml_content)
    for item in workflow_config["functions"]:
        if item["name"] == "simple_rag":
            rag_provider = item["parameters"]["properties"]["rag_provider"]["enum"][0]
            break

    rag_client = RAGSimple(rag_settings, rag_provider, kb_path)
    if not rag_client.kb_exists():
        rag_client.add_documents([kb_document])

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

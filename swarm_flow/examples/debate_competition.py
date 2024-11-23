import asyncio

import sys

sys.path.append("..")

from modules.workflow import WorkflowExecutor

debug = False
yaml_file = "../data/debate_competition.yaml"

# Example of group chat
if __name__ == "__main__":
    # Load workflow configuration
    with open(yaml_file, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # Example of debate topic:
    # - Technology makes life better
    # - Law is more important than morality
    topic = input("\nThe topic for debate: ")
    context_variables = {"topic": topic}

    # Create a workflow executor
    executor = WorkflowExecutor(yaml_content=yaml_content, context_variables=context_variables, debug=debug)

    # Start the discussion
    discussion_over = False
    round_count = 0  # To prevent infinite discussions
    max_rounds = 20  # Maximum number of rounds

    while not discussion_over and round_count < max_rounds:
        # Execute workflow
        output = asyncio.run(executor.run())
        print(f"\n{output}")
        round_count += 1

        # Moderator checks if the discussion should end
        if context_variables.get("active_agent") == "Moderator" and "[END]" in output:
            discussion_over = True

    if debug:
        print("\n" + ("=" * 40) + "\n")
        conversation = "\n\n".join(context_variables.get("conversation", []))
        print(f'The topic for debate: {topic}\n\n{conversation}')

    if not discussion_over:
        print("\nModerator: Due to time constraints, we'll have to conclude our discussion here today. Thank you all for your insightful contributions!")

import asyncio

import sys

sys.path.append("../..")

from modules.workflow import WorkflowExecutor

debug = False
yaml_file = "../../data/cn/debate_competition.yaml"

# Example of group chat
if __name__ == "__main__":
    # Load workflow configuration
    with open(yaml_file, "r", encoding="utf-8") as f:
        yaml_content = f.read()

    # 辩论主题示例：
    # - 科技让生活更美好
    # - 法律比道德更重要
    topic = input("\n辩论主题：")
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
        if context_variables.get("active_agent") == "主持人" and "[结束]" in output:
            discussion_over = True

    if debug:
        print("\n" + ("=" * 40) + "\n")
        conversation = "\n\n".join(context_variables.get("conversation", []))
        print(f'辩论主题：{topic}\n\n{conversation}')

    if not discussion_over:
        print("\n主持人：由于时间关系，今天只能先讨论到这里。感谢各位的精彩发言！")

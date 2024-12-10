import json
import re
import jinja2
import yaml
import asyncio

from .swarm import Swarm
from .swarm.types import *
from .config import llm_settings
from .tools import *


class StepTask:
    def __init__(self, step, workflow):
        self.step = step
        self.workflow = workflow
        self.prerequisite = step.get("prerequisite", [])
        self.execution = step.get("execution", "sync")

    def render_template(self, template_string, variables):
        if template_string is None:
            return None
        template = self.workflow.jinja_env.from_string(template_string)
        return template.render(**variables)

    async def run(self):
        step = self.step
        context_variables = self.workflow.context_variables
        active_agent = self.render_template(step["agent"], context_variables)

        step_name = step["name"]
        agent_name = active_agent

        self.workflow.log(f"Executing '{step_name}' ...")
        self.workflow.set_status(f"Executing '{step_name}' ...")

        agent = self.workflow.agents[agent_name]
        agent_params = self.workflow.agent_params[agent_name]

        # The output variables
        output_var = step["output"]["name"]
        output_type = step["output"].get("type", "string")

        # Check if there is a 'for_each' loop
        if "for_each" in agent_params:
            for_each = agent_params["for_each"]
            loop_item = for_each["item"]
            loop_list = context_variables.get(for_each["list"].strip())
            if not isinstance(loop_list, list):
                self.workflow.set_status(f"Type error", f"{for_each['list']}' is not a list and cannot be traversed by ‘for_each’.", type="error")
                raise Exception(f"Type error, '{for_each['list']}' is not a list and cannot be traversed by ‘for_each’.")

            execution_mode = for_each.get("execution", "sync")

            context_variables[output_var] = []

            async def process_item(item):
                local_context = context_variables.copy()
                local_context[loop_item] = item
                local_output_var = for_each.get("output")
                instructions = self.render_template(agent.instructions, local_context)
                output = await self.workflow.completion(agent, instructions)
                # Process 'stop_character' (ignore the content after stop_character)
                stop_character = step.get("stop_character")
                if stop_character:
                    output = output.split(stop_character)[0]
                if local_output_var:
                    local_context[local_output_var] = output
                # Process 'format'
                output_format = for_each.get("format")
                if output_format:
                    output = self.render_template(output_format, local_context)
                context_variables[output_var].append(output)
                return output

            if execution_mode == "async":
                # Concurrent execution
                async def limited_process_item(item, semaphore):
                    async with semaphore:
                        return await process_item(item)

                tasks = [asyncio.create_task(limited_process_item(item, self.workflow.semaphore)) for item in loop_list]
                await asyncio.gather(*tasks)
            else:
                # Sequential execution
                for item in loop_list:
                    await process_item(item)

            output = "\n\n".join(context_variables[output_var])
            if output_type == "string":
                context_variables[output_var] = output
            elif output_type == "json":
                self.workflow.set_status(f"Type error", "'for_each' can only return a list or string.", type="error")
                raise Exception("Type error, 'for_each' can only return a list or string.")

        else:
            instructions = self.render_template(agent.instructions, context_variables)
            output = await self.workflow.completion(agent, instructions)

            # Process 'stop_character' (ignore the content after stop_character)
            stop_character = step.get("stop_character")
            if stop_character:
                output = output.split(stop_character)[0]

            if output_type == "list":
                output = self.workflow.extract_list(output)
                self.workflow.log("convert to list", f"{output}")
            elif output_type == "json":
                output = self.workflow.extract_json(output)
                self.workflow.log("convert to json", f"{json.dumps(output, indent=2, ensure_ascii=False)}")
                key = step["output"].get("key", "")
                if len(key) > 0:
                    self.workflow.log(f"output: {key} -> {output[key]}")
                    output = output[key]

            context_variables[output_var] = output

        # Execute post_processing function if specified
        post_processing = step["output"].get("post_processing", "")
        if len(post_processing) > 0:
            post_processing_func = getattr(self.workflow, post_processing)
            if callable(post_processing_func):
                output = post_processing_func(output)
                context_variables[output_var] = output
                self.workflow.output = output

        # Process 'format'
        output_format = step["output"].get("format")
        if output_format:
            output = self.render_template(output_format, context_variables)
            # The output type will be cast to 'string'
            context_variables[output_var] = output
            self.workflow.output = output

        # Process 'append_to'
        append_to = step["output"].get("append_to")
        if append_to:
            for item in append_to:
                var_name = item.get("variable")
                if var_name is None:
                    self.workflow.set_status("append_to: invalid variable name", type="error")
                    continue

                # Process 'format'
                output_format = item.get("format")
                if output_format:
                    output = self.render_template(output_format, context_variables)

                if context_variables.get(var_name) is None:
                    context_variables[var_name] = []
                context_variables[var_name].append(output)

        self.workflow.log(f"'{step_name}' has been completed.")

        # Mark step completed
        self.workflow.step_events[step_name].set()


class WorkflowExecutor:
    def __init__(self, yaml_content, max_concurrency=5, messages=None, context_variables=None,
                 stream=False, debug=False, status_callback=None, stream_callback=None):

        # Stream output
        self.stream = stream

        # Output debugging information
        self.debug = debug

        # Output intermediate status information with callback
        self.status_callback = status_callback
        self.stream_callback = stream_callback

        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment()

        # Parse YAML content
        self.workflow = yaml.safe_load(yaml_content)
        self.user_input = ""

        # Extract LLM settings
        llm_provider = self.workflow["workflow"]["llm_provider"]
        self.llm_settings = llm_settings[llm_provider]

        # Create Swarm client
        self.client = Swarm(base_url=self.llm_settings["base_url"], api_key=self.llm_settings["api_key"], workflow=self)

        # Maximum concurrent requests
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(self.max_concurrency)

        # Create the agents dictionary for use in subsequent steps
        self.agents = {}
        self.agent_params = {}
        for a in self.workflow["agents"]:
            functions = []
            for func_name in a["functions"]:
                func = self.get_function_from_name(func_name)
                if func is None:
                    continue
                functions.append(func)

            # Create agent
            agent = Agent(
                name=a["name"],
                description=a["description"],
                model=self.llm_settings["default_model"],
                instructions=a["instruction"],
                functions=functions,
            )

            # Save agent for referencing in workflow
            self.agents[a["name"]] = agent
            self.agent_params[a["name"]] = a

        # Initialize the context used to pass variables between steps
        self.context_variables = {} if context_variables is None else context_variables

        # Set global variables
        if self.workflow.get("global_variables"):
            self.context_variables.update(self.workflow["global_variables"])

        # The final output of the workflow
        self.output = ""

        # Initialize historical dialogue
        self.messages = [] if messages is None else messages

        # Sort the steps according to the 'order' field
        self.steps = sorted(self.workflow["steps"], key=lambda x: x["order"])

        # Build a dictionary for steps to access by name
        self.steps_dict = {step["name"]: step for step in self.steps}

        # Create tasks for all steps
        self.step_tasks = {step["name"]: StepTask(step, self) for step in self.steps}

        # Create event and task mapping for step
        self.step_events = {step["name"]: asyncio.Event() for step in self.steps}
        self.step_futures = {}

    def extract_list(self, text):
        res = None

        patterns = [
            r"^\s*\d+\.\s*(.*\S)",  # Match “1. xxxx”
            r"^\s*-\s*(.*\S)",  # Match “ - xxxx”
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            if len(matches) < 1:
                continue
            res = list()
            res.extend(matches)
            break

        return res

    def extract_json(self, text):
        res = None

        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start < 0 or json_end < 1:
            return res

        res = json.loads(text[json_start:json_end+1])

        return res

    def log(self, status, details=None):
        if not self.debug:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if details is None:
            message = f"{status}"
        else:
            message = f"{status}\n```\n{details.strip()}\n```"
        print(f"\033[97m[\033[90m{timestamp}\033[97m]\033[90m\n{message}\033[0m")

    def set_status(self, status, details=None, type="info"):
        """ type: 'info', 'success', 'warning', 'error' """

        if not self.status_callback or not callable(self.status_callback):
            return

        if details is None:
            message = f"{status}"
        else:
            message = f'{status}:\n```\n{details.strip("```")}\n```'
        self.status_callback(message, type)

    def build_messages(self, instructions, history_length=100):
        if history_length is None:
            history_length = 100

        messages = []
        if len(instructions) > 0:
            messages.append({"role": "system", "content": instructions})
        if history_length > 0:
            for item in self.messages[-history_length:]:
                messages.append(item)
        return messages

    def get_function_from_name(self, func_name):
        for func in self.workflow.get("functions", []):
            if func["name"] == func_name:
                return func
        return None

    def transfer_to_agent(self, agent_name, query):
        self.log(f"TRANSFER -> {agent_name}", query)
        self.context_variables["transfer_to"] = {"status": f"Transfer to '{agent_name}'", "details": query}

        agent = self.agents.get(agent_name)
        if agent is None:
            return None
        agent_params = self.agent_params[agent_name]
        messages = self.build_messages(query, agent_params.get("history_length"))
        return self.client.run(agent, messages, context_variables=self.context_variables, stream=False, debug=self.debug)

    def default_stream_callback(self, chunk):
        if "content" in chunk and chunk["content"] is not None:
            print(chunk["content"], end="", flush=True)

        if "delim" in chunk and chunk["delim"] == "end":
            print()  # End of response message

    def process_streaming_response(self, response):
        for chunk in response:
            if self.stream_callback and callable(self.stream_callback):
                self.stream_callback(chunk)
            else:
                self.default_stream_callback(chunk)
            if "response" in chunk:
                return chunk["response"]

    async def completion(self, agent, instructions):
        self.log("instruction", instructions)

        agent_params = self.agent_params[agent.name]
        messages = self.build_messages(instructions, agent_params.get("history_length"))
        context_variables = self.context_variables
        model_override = None
        response = await asyncio.to_thread(
            self.client.run, agent, messages, context_variables, model_override, self.stream, self.debug
        )

        if self.stream:
            response = self.process_streaming_response(response)

        self.output = response.messages[-1]["content"].strip()
        self.log("output", f"{self.output}")

        transfer_to = self.context_variables.pop("transfer_to", None)
        if transfer_to:
            self.set_status(f'{transfer_to["status"]}', f'{transfer_to["details"]}', type="warning")
        self.set_status(f"{agent.name}", f"{self.output}", type="success")

        return self.output

    async def execute_step(self, step_name):
        step_task = self.step_tasks[step_name]
        # Waiting for the pre-steps to complete
        for dep in step_task.prerequisite:
            await self.step_events[dep].wait()

        if step_task.execution == "async":
            # Asynchronous execution
            async with self.semaphore:
                await step_task.run()
        else:
            # Synchronize execution
            await step_task.run()

    async def execute_workflow(self):
        pending_steps = set(step["name"] for step in self.steps)
        while pending_steps:
            scheduled_in_this_round = False
            for step in self.steps:
                step_name = step["name"]
                if step_name not in pending_steps:
                    continue
                step_task = self.step_tasks[step_name]
                prerequisite = step_task.prerequisite
                if all(self.step_events[pre].is_set() for pre in prerequisite):
                    # Pre-step completed
                    pending_steps.remove(step_name)
                    scheduled_in_this_round = True
                    if step_task.execution == "async":
                        # Asynchronous execution
                        task = asyncio.create_task(self.execute_step(step_name))
                        self.step_futures[step_name] = task
                    else:
                        # Synchronize execution
                        await self.execute_step(step_name)
            if not scheduled_in_this_round:
                # Check if there are any running tasks
                if any(not task.done() for task in self.step_futures.values()):
                    # Waiting for task completion
                    await asyncio.sleep(0.1)
                else:
                    # Unable to schedule new step and there are no running tasks, there may be a cyclic dependency
                    self.set_status(f"Unable to execute workflow, there may be a circular dependency.", type="error")
                    raise Exception("Unable to execute workflow, there may be a circular dependency.")
            else:
                # Give up control and execute the scheduled task
                await asyncio.sleep(0)
        # Waiting for all asynchronous tasks to complete
        if self.step_futures:
            await asyncio.gather(*self.step_futures.values())

    async def run(self, user_input="", max_retry=3):
        self.user_input = user_input.strip()
        self.context_variables.update({"user_input": user_input})

        if len(self.user_input) > 0:
            self.messages.append({"role": "user", "content": self.user_input})

        retry = 0
        while retry < max_retry:
            retry += 1
            try:
                self.output = ""
                await self.execute_workflow()
                self.messages.append({"role": "assistant", "content": self.output})
                break
            except Exception as e:
                self.output = ""
                self.log("WorkflowExecutor.run() caused an exception", f"{e}")
                self.log(f"retry ({retry}/{max_retry}) ...")
                self.set_status(f"WorkflowExecutor.run() caused an exception, retry ({retry}/{max_retry}) ...", f"{e}", type="error")

        self.set_status("All steps have been completed.")

        return self.output

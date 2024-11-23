import streamlit as st
import json
import yaml
import asyncio

from modules.workflow import WorkflowExecutor


# Set page layout
st.set_page_config(layout="wide")


# Refresh Function
def refresh_func(idx):
    if 'yaml_data' in st.session_state:
        functions = st.session_state['yaml_data'].get('functions', [])
        if 0 <= idx < len(functions):
            func = functions[idx]
            func_name_key = f'func_{idx}_name'
            func_desc_key = f'func_{idx}_description'
            func['name'] = st.session_state.get(func_name_key, func.get('name', ''))
            func['description'] = st.session_state.get(func_desc_key, func.get('description', ''))
            st.session_state['yaml_data']['functions'][idx] = functions


# Delete Function
def delete_func(idx):
    if 'yaml_data' in st.session_state:
        functions = st.session_state['yaml_data'].get('functions', [])
        if 0 <= idx < len(functions):
            functions.pop(idx)
            st.session_state['yaml_data']['functions'] = functions

# Refresh Agent
def refresh_agent(idx):
    if 'yaml_data' in st.session_state:
        agents = st.session_state['yaml_data'].get('agents', [])
        if 0 <= idx < len(agents):
            agent = agents[idx]
            agent_name_key = f'agent_{idx}_name'
            agent_desc_key = f'agent_{idx}_description'
            agent['name'] = st.session_state.get(agent_name_key, agent.get('name', ''))
            agent['description'] = st.session_state.get(agent_desc_key, agent.get('description', ''))
            st.session_state['yaml_data']['agents'][idx] = agent


# Delete Agent
def delete_agent(idx):
    if 'yaml_data' in st.session_state:
        agents = st.session_state['yaml_data'].get('agents', [])
        if 0 <= idx < len(agents):
            agents.pop(idx)
            st.session_state['yaml_data']['agents'] = agents

# Refresh Step
def refresh_step(idx):
    if 'yaml_data' in st.session_state:
        steps = st.session_state['yaml_data'].get('steps', [])
        if 0 <= idx < len(steps):
            step = steps[idx]
            step_name_key = f'step_{idx}_name'
            step_desc_key = f'step_{idx}_description'
            step['name'] = st.session_state.get(step_name_key, step.get('name', ''))
            step['description'] = st.session_state.get(step_desc_key, step.get('description', ''))
            st.session_state['yaml_data']['steps'][idx] = step

# Delete Step
def delete_step(idx):
    if 'yaml_data' in st.session_state:
        steps = st.session_state['yaml_data'].get('steps', [])
        if 0 <= idx < len(steps):
            steps.pop(idx)
            st.session_state['yaml_data']['steps'] = steps

# Load existing agents
def step_get_agent(step_name):
    step_agents = st.session_state['yaml_data'].get('agents', [])
    all_steps = st.session_state['yaml_data'].get('steps', [])

    agent_name_list = [agent["name"] for agent in step_agents]
    for step in all_steps:
        if step['name'] != step_name:
            continue
        if '{{' in step['agent'] and '}}' in step['agent'] and not step['agent'] in agent_name_list:
            agent_name_list.append(step['agent'])
        for i, agent_name in enumerate(agent_name_list):
            if agent_name != step['agent']:
                continue
            return agent_name_list, i

    return agent_name_list, 0

def init_chat_history():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.context_variables = {}
    return st.session_state.messages

def clear_chat_history():
    del st.session_state.messages

def set_context_variables(context_variables):
    variables = yaml.safe_load(context_variables)
    for key in variables.keys():
        st.session_state.context_variables[key] = variables[key]

def set_status(message, type="info"):
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)

# Initialize YAML data in session state
if 'yaml_data' not in st.session_state:
    st.session_state['yaml_data'] = {
        'workflow': {
            'version': "1.0",
            'name': "Multi-agent workflow",
            'description': "Multi-agent collaboration and workflow orchestration"
        },
        'llm_settings': {
            'provider': "openai"
        },
        'functions': [],
        'agents': [],
        'steps': []
    }

# Initialize uploader_key
if 'uploader_key' not in st.session_state:
    st.session_state['uploader_key'] = 0

# Edit / Test
tabs = st.tabs(["Edit", "Test"])

# tabs[0]：Edit and save YAML
with tabs[0]:
    # Load YAML file
    uploaded_file = st.file_uploader("Load YAML file", type=['yaml', 'yml'], key=st.session_state['uploader_key'])
    if uploaded_file is not None:
        yaml_content = uploaded_file.read().decode('utf-8')
        st.session_state['yaml_data'] = yaml.safe_load(yaml_content)
        st.session_state['uploader_key'] += 1

    st.divider()

    workflow_tabs = st.tabs(["Workflow", "LLM Settings", "Functions", "Agents", "Steps"])

    # Edit Workflow
    with workflow_tabs[0]:
        st.subheader("Workflow")
        workflow = st.session_state['yaml_data'].get('workflow', {})
        workflow['version'] = st.text_input("Version", value=workflow.get('version', ''), key='workflow_version')
        workflow['name'] = st.text_input("Name", value=workflow.get('name', ''), key='workflow_name')
        workflow['description'] = st.text_area("Description", value=workflow.get('description', ''), key='workflow_description')
        st.session_state['yaml_data']['workflow'] = workflow

    # Edit LLM Settings
    with workflow_tabs[1]:
        st.subheader("LLM Settings")
        llm_settings = st.session_state['yaml_data'].get('llm_settings', {})
        llm_settings['provider'] = st.text_input("Provider", value=llm_settings.get('provider', ''), key='llm_provider')
        st.session_state['yaml_data']['llm_settings'] = llm_settings

    # Edit Functions
    with workflow_tabs[2]:
        st.subheader("Functions")
        functions = st.session_state['yaml_data'].get('functions', [])

        # Add Function
        if st.button("＋ Add Function", key='add_function'):
            functions.append({
                'name': '',
                'description': '',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'param1': {
                            'description': 'param1',
                            'type': 'string'
                        }
                    },
                    'required': ['param1']
                }
            })
            st.session_state['yaml_data']['functions'] = functions

        # Display all functions
        for idx, func in enumerate(functions):
            func_name = func.get('name', '')
            if len(func_name) < 1:
                func_name = f"Function-{idx + 1}"
                func['name'] = func_name
            func_desc = func.get('description', '')
            func_expander = st.expander(f"{func_name}(): {func_desc}", expanded=False)
            with func_expander:
                # Delete / Refresh, using callback function
                col_refresh_delete = st.columns([0.5, 0.5])
                with col_refresh_delete[0]:
                    st.button("Delete Function", key=f'delete_func_{idx}', on_click=delete_func, args=(idx,))
                with col_refresh_delete[1]:
                    st.button("Refresh", key=f'refresh_func_{idx}', on_click=refresh_func, args=(idx,))

                func['name'] = st.text_input("Name", value=func.get('name', ''), key=f'func_name_{idx}')
                func['description'] = st.text_input("Description", value=func.get('description', ''), key=f'func_description_{idx}')
                parameters = st.text_area('Parameters', value=yaml.dump(func['parameters'], allow_unicode=True), key=f'func_parameters_{idx}')
                func['parameters'] = yaml.safe_load(parameters)

        st.session_state['yaml_data']['functions'] = functions

    # Edit Agents
    with workflow_tabs[3]:
        st.subheader("Agents")
        agents = st.session_state['yaml_data'].get('agents', [])

        # Add Agent
        if st.button("＋ Add Agent", key='add_agent'):
            agents.append({
                'name': '',
                'description': '',
                'system': '',
                'instruction': '',
                'output': {},
                'functions': []
            })
            st.session_state['yaml_data']['agents'] = agents

        # Display all agents
        for idx, agent in enumerate(agents):
            agent_name = agent.get('name', '')
            if len(agent_name) < 1:
                agent_name = f"Agent-{idx + 1}"
                agent['name'] = agent_name
            agent_desc = agent.get('description', '')
            agent_output = agent['output']
            agent_expander = st.expander(f"Output - {agent_output.get('type', 'string')}, {agent_name}: {agent_desc}", expanded=False)
            with agent_expander:
                # Delete / Refresh, using callback function
                col_refresh_delete = st.columns([0.5, 0.5])
                with col_refresh_delete[0]:
                    st.button("Delete Agent", key=f'delete_agent_{idx}', on_click=delete_agent, args=(idx,))
                with col_refresh_delete[1]:
                    st.button("Refresh", key=f'refresh_agent_{idx}', on_click=refresh_agent, args=(idx,))

                agent['name'] = st.text_input("Name", value=agent.get('name', ''), key=f'agent_name_{idx}')
                agent['description'] = st.text_input("Description", value=agent.get('description', ''), key=f'agent_description_{idx}')
                agent['system'] = st.text_area("System", value=agent.get('system', ''), key=f'agent_system_{idx}')
                agent['instruction'] = st.text_area("Instruction", value=agent.get('instruction', ''), key=f'agent_instruction_{idx}')

                # Edit output field
                st.markdown("**Output**")
                output = agent.get('output', {})
                output['name'] = st.text_input("Output Name", value=output.get('name', ''), key=f'agent_output_name_{idx}')
                type_list = ['string', 'json', 'list']
                type_index = 0
                for i, type_name in enumerate(type_list):
                    if type_name == output.get('type', 'string'):
                        type_index = i
                        break
                output['type'] = st.selectbox("Output Type", options=type_list, index=type_index, key=f'agent_output_type_{idx}')
                output['key'] = st.text_input("Output Key (for json type)", value=output.get('key', ''), key=f'agent_output_key_{idx}')
                agent['output'] = output

                # Edit functions field
                st.markdown("**Functions**")
                functions = st.text_area("Each function takes one line", value='\n'.join(agent.get('functions', [])), key=f'agent_functions_{idx}')
                agent['functions'] = functions.split('\n') if functions else []

        st.session_state['yaml_data']['agents'] = agents

    # Edit Steps
    with workflow_tabs[4]:
        st.subheader("Steps")
        steps = st.session_state['yaml_data'].get('steps', [])

        # Add Step
        if st.button("＋ Add Step", key='add_step'):
            steps.append({
                'name': '',
                'description': '',
                'order': 1,
                'agent': '',
                'execution': 'sync',
                'prerequisite': []
            })
            st.session_state['yaml_data']['steps'] = steps

        # Display all steps
        for idx, step in enumerate(steps):
            step_name = step.get('name', '')
            if len(step_name) < 1:
                step_name = f"Step-{idx + 1}"
                step['name'] = step_name
            step_order = step.get('order', 1)
            step_agent = step.get('agent', '')
            step_desc = step.get('description', '')
            step_expander = st.expander(f"Order - {step_order}, {step_agent}, {step_name}: {step_desc}", expanded=False)
            with step_expander:
                # Delete / Refresh, using callback function
                col_refresh_delete = st.columns([0.5, 0.5])
                with col_refresh_delete[0]:
                    st.button("Delete Step", key=f'delete_step_{idx}', on_click=delete_step, args=(idx,))
                with col_refresh_delete[1]:
                    st.button("Refresh", key=f'refresh_step_{idx}', on_click=refresh_step, args=(idx,))

                all_agents, selected_agent = step_get_agent(step_name)
                step['name'] = st.text_input("Name", value=step.get('name', ''), key=f'step_name_{idx}')
                step['description'] = st.text_input("Description", value=step.get('description', ''), key=f'step_description_{idx}')
                step['order'] = st.number_input("Order", value=step.get('order', 1), key=f'step_order_{idx}')
                step['agent'] = st.selectbox("Agent", options=all_agents, index=selected_agent, key=f'step_agent_{idx}')
                step['execution'] = st.selectbox("Execution", options=['sync', 'async'], index=0 if step.get('execution') == 'sync' else 1, key=f'step_execution_{idx}')

                # Edit prerequisite field
                st.markdown("**Predecessor Steps**")
                prerequisite = st.text_area("Each step takes one line", value='\n'.join(step.get('prerequisite', [])), key=f'step_prerequisite_{idx}')
                step['prerequisite'] = prerequisite.split('\n') if prerequisite else []

        st.session_state['yaml_data']['steps'] = steps

    st.divider()

    # Save to YAML file
    yaml_str = yaml.dump(st.session_state['yaml_data'], allow_unicode=True)
    st.download_button("Save", data=yaml_str, file_name="workflow.yaml", mime="text/yaml")

# tabs[1]：Run workflow and output results
with tabs[1]:
    init_chat_history()

    st.write("Click the 'YAML' button to view the complete YAML content")
    if st.button("YAML", key='run_workflow'):
        st.write(st.session_state['yaml_data'])

    # Preset Context Variables
    st.markdown("**Preset Context Variables**")
    context_variables = st.text_area('Each variable takes one line', value='"key1": "value1"')
    st.button("Apply", on_click=set_context_variables, args=[context_variables])

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    placeholder_user = st.empty()
    placeholder_assistant = st.empty()

    st.divider()
    st.markdown("**User Input**")
    user_input = st.chat_input("<Enter> to send, <Shift+Enter> to wrap")
    st.button("Clear", on_click=clear_chat_history)
    st.divider()

    if user_input:
        # Create and run a workflow executor
        executor = WorkflowExecutor(
            yaml_content=json.dumps(st.session_state['yaml_data']),
            messages=st.session_state.messages,
            context_variables=st.session_state.context_variables,
            status_callback=set_status,
        )

        output = asyncio.run(executor.run(user_input))

        if len(user_input.strip()) > 0:
            with placeholder_user.chat_message(st.session_state.messages[-2]["role"]):
                st.markdown(st.session_state.messages[-2]["content"])
        with placeholder_assistant.chat_message(st.session_state.messages[-1]["role"]):
            st.markdown(st.session_state.messages[-1]["content"])

    if st.session_state.context_variables is not None:
        st.write("context variables: ")
        st.json(st.session_state.context_variables)

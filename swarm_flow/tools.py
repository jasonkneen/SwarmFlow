import pytz
import requests
import io
import contextlib
from openai import OpenAI
from duckduckgo_search import DDGS
from datetime import datetime
from bs4 import BeautifulSoup

from .rag.rag_simple import RAGSimple
from .config import llm_settings, rag_settings, tool_settings

rag_clients = {}
def simple_rag(rag_provider: str, kb_path: str, kb_name: str, query: str) -> str:
    """
    Retrieve information from the knowledge base.
    :param rag_provider:
    :param kb_path:
    :param kb_name:
    :param query:
    :return: Results retrieved from the knowledge base.
    """
    global rag_clients

    rag_client = rag_clients.get(rag_provider)
    if rag_client is None:
        rag_client = RAGSimple(rag_settings, rag_provider, kb_path)
        rag_clients[rag_provider] = rag_client

    knowledge_snippets = rag_client.search([query], top_k=5, kb_name=kb_name)
    return "\n\n".join(knowledge_snippets["documents"][0])

def describe_image(llm_provider: str, image_link: str, instruction: str) -> str:
    """
    Get the image from network and describe the image content.
    :param llm_provider:
    :param image_link:
    :param instruction:
    :return: Description of the image.
    """
    llm_params = llm_settings[llm_provider]
    client = OpenAI(base_url=llm_params["base_url"], api_key=llm_params["api_key"])
    response = client.chat.completions.create(
        model=llm_params["default_model"],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "image_url", "image_url": {"url": image_link}}
                ]
            }
        ],
        max_tokens=500
    )
    return response.choices[0].message.content

def execute_python_code(code: str) -> str:
    """
    Execute python code, return execution result or error message.
    :param code: A string containing Python code to execute.
    :return: The output or error message from executing the Python code.
    """
    # Capture the standard output
    stdout = io.StringIO()

    try:
        # Redirect stdout to the StringIO object to capture print statements
        with contextlib.redirect_stdout(stdout):
            exec(code)

        # Fetch the standard output
        output = stdout.getvalue()
        if output == '':
            return "I executed your python code but the result is: ''. Use print() to output the variable or result!"
        else:
            return f"python'''\n {code}\n'''\nPython code obtained this result: '''{output}'''."

    except Exception as e:
        # In case of an exception, return the error message
        output = f"Error: {e}"
    finally:
        stdout.close()

    return f"I executed the python code and obtained this result: '''{output}'''."

def date(timezone: str="America/New_York") -> str:
    """
    Gets the current date and time. If a time zone is specified, the time in that time zone is returned.
    :param timezone: The timezone for which to get the current time (e.g., ’UTC‘, 'America/New_York').
    :return: Formatted current date and time.
    """
    if timezone:
        # Get the current time in the specified timezone
        tz = pytz.timezone(timezone)
        current_datetime = datetime.now(tz)
    else:
        # Get the current date and time in the local timezone
        current_datetime = datetime.now()

    return current_datetime.strftime("%A, %m/%d/%Y %I:%M %p")

def date_cn(timezone: str="Asia/Shanghai") -> str:
    """
    获取当前日期和时间。如果指定了时区，则返回该时区的时间。
    :param timezone: The timezone for which to get the current time (e.g., ’UTC‘, 'America/New_York').
    :return: Formatted current date and time.
    """
    def get_weekday(t):
        weekday_dict = {
            0: "星期一",
            1: "星期二",
            2: "星期三",
            3: "星期四",
            4: "星期五",
            5: "星期六",
            6: "星期日"
        }
        weekday = weekday_dict[t.weekday()]
        return weekday

    if timezone:
        # Get the current time in the specified timezone
        tz = pytz.timezone(timezone)
        current_datetime = datetime.now(tz)
    else:
        # Get the current date and time in the local timezone
        current_datetime = datetime.now()

    return current_datetime.strftime("Date: %Y-%m-%d, Time: %H:%M:%S") + f", Week: {get_weekday(current_datetime)})"

def web_content(url: str) -> str:
    """
    Retrieve the textual content from the webpage.
    :param url: The web page link.
    :return: Text content in the web pages.
    """
    text = ""
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to retrieve the content from '{url}', status code: {response.status_code}")
        return text

    # Using html.parser to parse webpage content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Retrieve all textual content of the webpage
    content = soup.get_text().strip()
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        text += f"{line}\n"

    while text.find("\n\n\n") >= 0:
        text = text.replace("\n\n\n", "\n\n")

    if len(text) < 1:
        print(f"Failed to retrieve the content from '{url}'")

    return text

def web_search_ddg(query: str) -> dict:
    """
    Retrieve the latest information from the internet.
    Use DuckDuckGo Search API.
    :param query: Input string of the objective.
    :return: Json format data, including search results and error message.
    """
    proxy = tool_settings.get("web_search_proxy", "")
    if len(proxy.strip()) < 1:
        proxy = None

    try:
        result_list = []
        with DDGS(proxy=proxy) as ddgs:
            results = ddgs.news(query, region='cn-zh', max_results=10)

        for result in results:
            # Search results include url, title, and description of relevant web pages.
            result_data = {
                "source": result["url"],
                "title": result["title"],
                "description": result["body"],
            }
            result_list.append(result_data)

        return {"results": result_list, "error": ""}

    except Exception as e:
        # Return the error message if an exception occurs
        return {"results": [], "error": str(e)}

def web_search_searxng(query: str, num_results: int=5) -> dict:
    """
    Retrieve the latest information from the internet.
    Use SearxNG Search API.
    :param query: Input string of the objective.
    :param num_results: The number of results returned.
    :return: Json format data, including search results and error message.
    """
    proxy = None
    web_search_proxy = tool_settings.get("web_search_proxy", "")
    if len(web_search_proxy.strip()) > 0:
        proxy = {
            "http": web_search_proxy,
            "https": web_search_proxy,
        }

    url = tool_settings["searxng"]["base_url"]
    params = {
        "q": query,
        "format": "json",
        "engines": tool_settings["searxng"]["search_engine"],
        "num_results": num_results
    }

    try:
        response = requests.get(url, params=params, proxies=proxy)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", [])[:num_results]:
            # Search results include url, title, and content of relevant web pages.
            results.append({
                "source": result.get("url"),
                "title": result.get("title"),
                "content": result.get("content")
            })

        return {"results": results, "error": ""}
    except requests.RequestException as e:
        # Return the error message if an exception occurs
        return {"results": [], "error": str(e)}

def web_search(query: str) -> dict:
    """
    Retrieve the latest information from the internet.
    :param query: Input string of the objective.
    :return: Json format data, including search results and error message
    """
    web_search_api = tool_settings.get("web_search_api", "duckduckgo")
    if web_search_api == "duckduckgo":
        return web_search_ddg(query)
    elif web_search_api == "searxng":
        return web_search_searxng(query)
    else:
        print(f"Invalid web search settings: {web_search_api}")
        return {"results": [], "error": f"Invalid web search settings: {web_search_api}"}

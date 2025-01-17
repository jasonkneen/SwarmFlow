llm_settings = {
    "openai": {
        "base_url": "",  # To invoke the OpenAI API directly, leave this field as an empty string
        "api_key": "sk-xxxx",  # Enter a valid API Key here
        "default_model": "gpt-4o",  # The o1 model does not support function call, so the gpt-4o model is recommended
        "temperature": 0.7,
        "max_context_tokens": 8192,
        "max_new_tokens": 1024,
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "ollama-api-key",
        "default_model": "qwen2.5:14b",
        "temperature": 0.7,
        "max_context_tokens": 8192,
        "max_new_tokens": 1024,
    },
}

rag_settings = {
    "openai": {
        "base_url": "",  # To invoke the OpenAI API directly, leave this field as an empty string
        "api_key": "sk-xxxx",  # Enter a valid API Key here
        "embedding_model": "text-embedding-ada-002",
    },
    "ollama": {
        "host": "localhost:11434",
        "embedding_model": "bge-m3:latest",
    },
    "local": {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    },
}

tool_settings = {
    # If DuckDuckGo cannot be accessed, you need to set up a proxy first.
    "web_search_api": "duckduckgo",  # duckduckgo / searxng
    "web_search_proxy": "http://127.0.0.1:7890",
    # If using Searxng, you should first set up the environment. For installation and configuration, please refer to: https://docs.searxng.org/
    "searxng": {
        "base_url": "http://localhost:8888/search",
        "search_engine": "google",  # You can specify different search engines (such as 'google'), default is 'general'
    }
}

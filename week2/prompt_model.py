import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_BASE_URL = os.getenv("GOOGLE_BASE_URL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

GOOGLE_GEMINI_MODELS = {
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
}

OLLAMA_MODELS = {
    "llama3.1",
    "phi3",
    "deepseek-r1:1.5b",
    "gemma3:4b",
    "deepseek-r1:7b",
}


def _detect_model(model: str) -> str:

    model_lower = model.lower()

    if model_lower in GOOGLE_GEMINI_MODELS or model_lower.startswith("gemini"):
        return "gemini"

    if model_lower in OLLAMA_MODELS:
        return "ollama"

    return "gemini" if "gemini" in model_lower else "ollama"


def _prompt_gemini(model: str, prompt: str) -> str:

    if not GOOGLE_API_KEY:
        return (
            "Error: GOOGLE_API_KEY environment variable is not set. "
            "Export it before running: export GOOGLE_API_KEY='your-key-here'"
        )

    url = f"{GOOGLE_BASE_URL}/{model}:generateContent?key={GOOGLE_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    usage = data.get("usageMetadata", {})
    prompt_tokens = usage.get("promptTokenCount")
    output_tokens = usage.get("candidatesTokenCount")

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, prompt_tokens, output_tokens
    except KeyError, IndexError:
        return f"Error: Unexpected Gemini response structure: {data}", None, None


def _prompt_ollama(model: str, prompt: str) -> str:

    url = f"{OLLAMA_BASE_URL}/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()

    prompt_tokens = data.get("prompt_eval_count")
    output_tokens = data.get("eval_count")

    try:
        text = data["response"]
        return text, prompt_tokens, output_tokens
    except KeyError:
        return f"Error: Unexpected Ollama response structure: {data}", None, None


def prompt_model(model: str, prompt: str) -> str:

    model_detect = _detect_model(model)

    try:
        if model_detect == "gemini":
            return _prompt_gemini(model, prompt)
        else:
            return _prompt_ollama(model, prompt)

    except requests.exceptions.ConnectionError as e:
        if model_detect == "ollama":
            return (
                f"Error: Could not connect to Ollama at {OLLAMA_BASE_URL}. "
                "Make sure Ollama is running (`ollama serve`). "
                f"Details: {e}",
                None,
                None,
            )
        return f"Error: Connection failed for {model}: {e}", None, None

    except requests.exceptions.Timeout:
        return (
            f"Error: Request to {model} timed out. Try again or use a shorter prompt.",
            None,
            None,
        )

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = e.response.text[:300] if e.response is not None else ""
        return f"Error: HTTP {status} from {model}. {body}", None, None

    except Exception as e:
        return (
            f"Error: Unexpected error while prompting {model}: {type(e).__name__}: {e}",
            None,
            None,
        )


def main():

    if len(sys.argv) < 3:
        print(
            "Error: The command should [uv run | python] prompt_mode.py <model> <prompts>"
        )
        sys.exit(1)

    prompt = sys.argv[2]
    model = sys.argv[1]

    if model not in GOOGLE_GEMINI_MODELS and model not in OLLAMA_MODELS:
        print("The model does not exist here. Try another model.")
        sys.exit(1)

    print("--- RESPONSE ---")

    text, prompt_tokens, output_tokens = prompt_model(model, prompt)
    print(text)
    print(f"--- TOKENS: prompt={prompt_tokens} output={output_tokens} ---")


if __name__ == "__main__":
    main()

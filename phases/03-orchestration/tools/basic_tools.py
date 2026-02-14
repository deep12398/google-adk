from typing import Dict


def get_weather(city: str) -> Dict[str, str]:
    """Demo tool: return a stubbed weather response."""
    return {
        "city": city,
        "forecast": f"Sunny in {city} (demo)",
    }


def say_hello(name: str) -> Dict[str, str]:
    return {"message": f"Hello, {name}!"}


def say_goodbye(name: str) -> Dict[str, str]:
    return {"message": f"Goodbye, {name}!"}

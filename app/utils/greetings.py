def greet(name: str, formal: bool = False) -> str:
    name = name.strip().title()
    if formal:
        return f"Good day, {name}."
    return f"Hello, {name}!"
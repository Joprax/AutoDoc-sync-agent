def greet(name: str, formal: bool = False) -> str:
    """Returns a greeting for the given name, formal or casual."""
    return f"Good day, {name}." if formal else f"Hello, {name}!"
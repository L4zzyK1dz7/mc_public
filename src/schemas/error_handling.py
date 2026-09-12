"""
This module provides a utility function to convert Pydantic validation errors
into human-readable error messages.
"""

from pydantic import ValidationError


def human_readable_errors(e: ValidationError) -> list[str]:
    """
    Convert a Pydantic ValidationError into a list of human-readable error messages.

    Args:
        e (ValidationError): The Pydantic ValidationError instance to process.

    Returns:
        list[str]: A list of human-readable error messages.
    """
    clean_messages = []  # Store human readable error messages

    for error in e.errors():
        # 1. Turn the tuple path ('items', 0, 'age') into a clean 'items[0].age' string
        path_elements = []

        for x in error["loc"]:
            if isinstance(x, int):
                path_elements.append(f"[{x}]")

            else:
                # If it's a field name, add a dot separator unless it's the very first item
                path_elements.append(
                    f".{x}"
                    if path_elements and not path_elements[-1].startswith("[")
                    else str(x)
                )
        readable_loc = "".join(path_elements)

        # 2. Clean up common technical phrasing patterns
        reason = error["msg"].replace(
            "Value error, ", ""
        )  # Strip internal validator prefix
        reason = reason.capitalize()

        # 3. Create a clean sentence
        if error["type"] == "missing":
            clean_messages.append(
                f"The field '{readable_loc}' is missing and required."
            )
        else:
            clean_messages.append(
                f"The field '{readable_loc}' is invalid. Reason: {reason}."
            )

    return clean_messages

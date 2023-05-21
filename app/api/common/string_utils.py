import os
import re


def tokenize_string(input_str: str, lower: bool = False) -> str:
    # Split the file name into name and extension
    name, extension = os.path.splitext(input_str)

    # Replace spaces with hypens in the name
    name_with_hypens = name.replace(r" +", "-")

    # Replace non-alphanumeric characters with hyphens in the name
    tokenized_name = re.sub(r"[^a-zA-Z0-9_]", "-", name_with_hypens)

    # Replace consecutive hyphens with a single hyphen in the name
    tokenized_name = re.sub(r"-+", "-", tokenized_name)

    # Convert to lowercase if specified
    if lower:
        tokenized_name = tokenized_name.lower()

    # Remove any leading or trailing hyphens in the name
    tokenized_name = tokenized_name.strip("-")

    # Rejoin the name and extension with a dot
    return tokenized_name + (f".{extension}" if extension else "")

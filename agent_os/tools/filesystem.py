import os
import shutil

def create_file(path: str, content: str = "") -> bool:
    """Creates a file with the given content."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

def read_file(path: str) -> str:
    """Reads the content of a file."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def delete_file(path: str) -> bool:
    """Deletes a file."""
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def file_exists(path: str) -> bool:
    """Checks if a file exists."""
    return os.path.exists(path)

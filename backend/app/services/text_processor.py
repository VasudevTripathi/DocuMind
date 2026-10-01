import re

def clean_text(text: str) -> str:
    """
    Cleans and normalizes extracted text.
    - Normalizes multiple whitespace characters and horizontal spacing
    - Normalizes line breaks (avoids ragged single-character line wraps while keeping paragraph breaks)
    - Removes non-printable / control noise while preserving meaningful punctuation
    - Preserves case and natural language context needed for NLP classification and LLM reasoning
    """
    if not text:
        return ""

    # Replace null bytes and non-printable control characters (except tabs and newlines)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Normalize carriage returns
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

    # Fix hyphenated line breaks (e.g., "organi-\nzation" -> "organization")
    cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', cleaned)

    # Replace runs of 3 or more newlines with double newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    # Normalize horizontal whitespace (spaces, tabs)
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    # Trim leading/trailing whitespace on each line
    lines = [line.strip() for line in cleaned.split('\n')]
    cleaned = '\n'.join(lines)

    # Clean redundant blank lines again
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()

def count_words(text: str) -> int:
    """Counts words in a cleaned text string."""
    if not text:
        return 0
    words = text.split()
    return len(words)

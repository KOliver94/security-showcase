import os
import random
import string
from datetime import datetime

FILES_FOLDER = "files"
NUM_FILES = 15
MIN_PARAGRAPHS = 1
MAX_PARAGRAPHS = 5

SAMPLE_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "We need to generate a random paragraph of text.",
    "This is a sample sentence for our text generator.",
    "Python makes it easy to work with files and strings.",
    "Security vulnerabilities can often be found in file handling code.",
    "Directory traversal is a common web application vulnerability.",
    "File systems are hierarchical structures to organize data.",
    "The path of least resistance is often the most vulnerable.",
    "Input validation is crucial for preventing security issues.",
    "Always sanitize user-provided paths before using them.",
    "Web servers should restrict access to sensitive system files.",
    "Documentation helps developers understand security implications.",
    "System configuration files often contain sensitive information.",
    "Proper access controls are essential for file security.",
    "Modern applications need to consider various attack vectors.",
    "Data breaches often start with a simple oversight.",
    "Code reviews are an important part of security practices.",
    "File permissions should follow the principle of least privilege.",
    "Cybersecurity is increasingly important in our connected world.",
    "Always assume user input could be malicious in nature."
]


def generate_random_filename():
    prefix = ''.join(random.choice(string.ascii_lowercase) for _ in range(random.randint(5, 10)))
    return f"{prefix}.txt"


def generate_random_paragraph():
    num_sentences = random.randint(3, 8)
    sentences = random.choices(SAMPLE_SENTENCES, k=num_sentences)
    return ' '.join(sentences)


def generate_random_content():
    num_paragraphs = random.randint(MIN_PARAGRAPHS, MAX_PARAGRAPHS)
    paragraphs = []

    for _ in range(num_paragraphs):
        paragraphs.append(generate_random_paragraph())

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    paragraphs.append(f"\nGenerated on: {timestamp}")

    return '\n\n'.join(paragraphs)


def generate_files():
    os.makedirs(FILES_FOLDER, exist_ok=True)
    print(f"Creating {NUM_FILES} random text files in '{FILES_FOLDER}' directory...")

    for i in range(NUM_FILES):
        filename = generate_random_filename()
        filepath = os.path.join(FILES_FOLDER, filename)

        while os.path.exists(filepath):
            filename = generate_random_filename()
            filepath = os.path.join(FILES_FOLDER, filename)

        content = generate_random_content()
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"Created: {filepath} ({len(content)} characters)")

    print("Done!")

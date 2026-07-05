"""
Avtomatik parol generatsiya qiluvchi
"""
import random
import string


def generate_password(length: int = 10) -> str:
    chars = (
        string.ascii_uppercase +
        string.ascii_lowercase +
        string.digits +
        "!@#$%"
    )
    # Kamida 1 ta har turdan
    password = [
        random.choice(string.ascii_uppercase),
        random.choice(string.ascii_lowercase),
        random.choice(string.digits),
        random.choice("!@#$%"),
    ]
    password += random.choices(chars, k=length - 4)
    random.shuffle(password)
    return "".join(password)

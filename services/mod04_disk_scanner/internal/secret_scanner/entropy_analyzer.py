"""Shannon Entropy Analyzer for High-Entropy Credential Detection."""

import math


def calculate_shannon_entropy(data: str) -> float:
    """Calculates Shannon entropy in bits per character.
    
    Random strings (API keys, private keys, hashes) typically have entropy > 4.5.
    """
    if not data:
        return 0.0

    entropy = 0.0
    length = len(data)
    frequencies = {}

    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1

    for count in frequencies.values():
        p_x = count / length
        entropy += -p_x * math.log2(p_x)

    return entropy


def is_high_entropy(data: str, min_length: int = 16, threshold: float = 4.5) -> bool:
    """Determines whether a token exhibits characteristic random cryptographic entropy."""
    if len(data) < min_length:
        return False
    return calculate_shannon_entropy(data) >= threshold


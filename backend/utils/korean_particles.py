"""
Utility functions for dynamic Korean particle selection.

Automatically selects the correct Korean particle (조사) based on whether
a word ends in a consonant (받침) or vowel.
"""


def has_final_consonant(text: str) -> bool:
    """
    Check if a Korean word ends with a final consonant (받침).

    Args:
        text: Korean text to check (uses the last character)

    Returns:
        True if the last character ends with a final consonant, False otherwise
    """
    if not text:
        return False

    last_char = text[-1]

    # Check if it's a Hangul character
    if not ("가" <= last_char <= "힣"):
        # For non-Korean characters (English, numbers, etc.),
        # default to consonant ending for safer grammar
        return True

    # Hangul Unicode calculation
    # Base: 0xAC00 (가), each character code = ((initial * 21) + medial) * 28 + final
    # If final == 0, no final consonant
    char_code = ord(last_char) - 0xAC00
    final_consonant = char_code % 28

    return final_consonant != 0


def format_with_particles(template: str, **kwargs) -> str:
    """
    Format a string template with dynamic Korean particle selection.

    Supports the following particle patterns in templates:
    - {name:은는} → 은 (consonant) or 는 (vowel)
    - {name:이가} → 이 (consonant) or 가 (vowel)
    - {name:을를} → 을 (consonant) or 를 (vowel)
    - {name:과와} → 과 (consonant) or 와 (vowel)
    - {name:으로로} → 으로 (consonant) or 로 (vowel)

    Examples:
        >>> format_with_particles("{name:이가} 말했다", name="프리렌")
        "프리렌이 말했다"

        >>> format_with_particles("{name:은는} 강하다", name="히메")
        "히메는 강하다"

        >>> format_with_particles("{name:으로로}서", name="치즈루")
        "치즈루로서"

    Args:
        template: String template with particle patterns
        **kwargs: Named arguments for variable substitution

    Returns:
        Formatted string with correct particles
    """
    result = template

    # Particle mappings: {pattern: (consonant_form, vowel_form)}
    particles = {
        "은는": ("은", "는"),
        "이가": ("이", "가"),
        "을를": ("을", "를"),
        "과와": ("과", "와"),
        "으로로": ("으로", "로"),
    }

    # Replace each variable with particle pattern
    for var_name, var_value in kwargs.items():
        for pattern, (consonant_form, vowel_form) in particles.items():
            placeholder = f"{{{var_name}:{pattern}}}"

            if placeholder in result:
                # Choose particle based on final consonant
                particle = consonant_form if has_final_consonant(var_value) else vowel_form
                result = result.replace(placeholder, var_value + particle)

        # Also replace simple placeholders without particles
        simple_placeholder = f"{{{var_name}}}"
        result = result.replace(simple_placeholder, var_value)

    return result

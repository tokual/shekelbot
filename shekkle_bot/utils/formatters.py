def escape_markdown(text):
    """Helper to escape markdown characters."""
    if not text:
        return ""
    # Escape characters like * _ ` [ ] ( ) ~ > # + - = | { } . !
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in str(text))

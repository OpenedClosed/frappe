


def format_crm_phone(normalize_numbers: str) -> str:
    """
    Преобразует номер в формат CRM: +48-XXX-XXX-XXX.
    Бросает исключение, если номер не польский.
    """
    if normalize_numbers.startswith("48") and len(normalize_numbers) == 11:
        core = normalize_numbers[2:]
    elif normalize_numbers.startswith("0") and len(normalize_numbers) == 9:
        core = normalize_numbers
    elif normalize_numbers.startswith("48") and len(normalize_numbers) == 10:
        raise ValueError("Неверный формат польского номера.")
    elif normalize_numbers.startswith("7"):
        raise ValueError("Российские номера не поддерживаются CRM")
    elif len(normalize_numbers) == 9:
        core = normalize_numbers
    else:
        raise ValueError(f"Недопустимый номер: {normalize_numbers}")

    return f"+48-{core[:3]}-{core[3:6]}-{core[6:]}"

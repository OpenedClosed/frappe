


# def format_crm_phone(normalize_numbers: str) -> str:
#     """
#     Преобразует номер в формат CRM: +48-XXX-XXX-XXX.
#     Бросает исключение, если номер не польский.
#     """
#     if normalize_numbers.startswith("48") and len(normalize_numbers) == 11:
#         core = normalize_numbers[2:]
#     elif normalize_numbers.startswith("0") and len(normalize_numbers) == 9:
#         core = normalize_numbers
#     elif normalize_numbers.startswith("48") and len(normalize_numbers) == 10:
#         raise ValueError("Неверный формат польского номера.")
#     elif normalize_numbers.startswith("7"):
#         raise ValueError("Российские номера не поддерживаются CRM")
#     elif len(normalize_numbers) == 9:
#         core = normalize_numbers
#     else:
#         raise ValueError(f"Недопустимый номер: {normalize_numbers}")

#     return f"+48-{core[:3]}-{core[3:6]}-{core[6:]}"

import re

import phonenumbers
from phonenumbers import NumberParseException

def format_crm_phone(number_raw: str) -> str:
    """
    Преобразует любой номер телефона в формат: +CC-XXX-XXX-XXXX с дефисами.
    Бросает исключение при некорректном номере.
    """
    try:
        parsed = phonenumbers.parse(number_raw, None)
        if not phonenumbers.is_possible_number(parsed):
            raise ValueError("Невозможный номер.")

        international = phonenumbers.format_number(
            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )  # например: +48 123 456 789

        digits_only = international.replace("+", "").replace("(", "").replace(")", "")
        parts = digits_only.split()

        if len(parts) < 2:
            raise ValueError("Невозможно отформатировать номер.")

        # Пример: ['48', '123', '456', '789']
        return "+" + "-".join(parts)

    except NumberParseException:
        raise ValueError("Невозможно распознать номер.")

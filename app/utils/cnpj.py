"""Utilidades para manipulação de CNPJ."""

from __future__ import annotations

import re

CNPJ_PATTERN = re.compile(r"\D")


def sanitize_cnpj(value: str) -> str:
    """Remove qualquer caractere não numérico do CNPJ."""
    return CNPJ_PATTERN.sub("", value or "")


def validate_cnpj(value: str) -> bool:
    """Valida um CNPJ utilizando o algoritmo oficial."""
    cnpj = sanitize_cnpj(value)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def calculate_digit(numbers: str) -> str:
        weights = list(range(len(numbers) - 7, 1, -1))
        total = sum(int(digit) * weight for digit, weight in zip(numbers, weights))
        remainder = total % 11
        return "0" if remainder < 2 else str(11 - remainder)

    first_digit = calculate_digit(cnpj[:12])
    second_digit = calculate_digit(cnpj[:12] + first_digit)
    return cnpj[-2:] == first_digit + second_digit

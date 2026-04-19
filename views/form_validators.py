# QA — Wayne Tong (24024786): validation rules.
# Helpers for email, password policy, and UK mobile numbers on forms and login.
# Centralised here for ease of use.
import re
from typing import List

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QRegularExpressionValidator
from PyQt5.QtWidgets import QLineEdit

# Compiled patterns reused on each validation call for efficiency.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_UK_MOBILE_RE = re.compile(r"^07\d{9}$")


def is_valid_email(email: str) -> bool:
    # Empty input is treated as invalid for mandatory email fields.
    if not email:
        return False
    # Pattern: local-part@domain.tld without whitespace.
    return _EMAIL_RE.match(email) is not None


def password_requirements(password: str) -> List[str]:
    # Returns a list of unmet policy clauses; an empty list indicates an acceptable password.
    unmet = []

    # Minimum length requirement
    if len(password) < 8:
        unmet.append("at least 8 characters")

    # Complexity requirements: mixed case, digit, and non-alphanumeric symbol.
    if not re.search(r"[A-Z]", password):
        unmet.append("an uppercase letter (A-Z)")
    if not re.search(r"\d", password):
        unmet.append("a number (0-9)")
    if not re.search(r"[^A-Za-z0-9]", password):
        unmet.append("a special character (e.g. !@#$...)")
    if not re.search(r"[a-z]", password):
        unmet.append("a lowercase letter (a-z)")

    return unmet


def normalize_uk_mobile(phone: str) -> str:
    # Strip leading, trailing, and internal spaces before length and pattern checks.
    return (phone or "").strip().replace(" ", "")


def is_valid_uk_mobile(phone: str) -> bool:
    # UK mobile convention: eleven digits beginning with 07.
    s = normalize_uk_mobile(phone)
    if len(s) != 11:
        return False
    return _UK_MOBILE_RE.match(s) is not None


def uk_mobile_format_hint() -> str:
    return "UK mobile: exactly 11 digits, starting with 07 (e.g. 07545798234)."


def attach_uk_mobile_input(line_edit: QLineEdit) -> None:
    # Restrict input to digits and eleven characters; submit-time validation enforces full format.
    line_edit.setMaxLength(11)
    line_edit.setValidator(
        QRegularExpressionValidator(QRegularExpression(r"^[0-9]*$"))
    )
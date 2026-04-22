"""
Unit tests for views/form_validators.py
QA — Wayne Tong (24017066)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from views.form_validators import (
    is_valid_email,
    is_valid_uk_mobile,
    normalize_uk_mobile,
    password_requirements,
)


class TestIsValidEmail(unittest.TestCase):
    def test_valid_email(self):
        self.assertTrue(is_valid_email("user@example.com"))

    def test_valid_email_subdomain(self):
        self.assertTrue(is_valid_email("user@mail.paragon-pams.uk"))

    def test_empty_string_is_invalid(self):
        self.assertFalse(is_valid_email(""))

    def test_missing_at_symbol(self):
        self.assertFalse(is_valid_email("userexample.com"))

    def test_missing_domain(self):
        self.assertFalse(is_valid_email("user@"))

    def test_whitespace_in_email(self):
        self.assertFalse(is_valid_email("user @example.com"))


class TestPasswordRequirements(unittest.TestCase):
    def test_strong_password_has_no_unmet_requirements(self):
        self.assertEqual(password_requirements("Secure#99"), [])

    def test_too_short(self):
        unmet = password_requirements("Ab1!")
        self.assertIn("at least 8 characters", unmet)

    def test_missing_uppercase(self):
        unmet = password_requirements("secure#99")
        self.assertIn("an uppercase letter (A-Z)", unmet)

    def test_missing_lowercase(self):
        unmet = password_requirements("SECURE#99")
        self.assertIn("a lowercase letter (a-z)", unmet)

    def test_missing_digit(self):
        unmet = password_requirements("Secure#!!")
        self.assertIn("a number (0-9)", unmet)

    def test_missing_special_character(self):
        unmet = password_requirements("Secure999")
        self.assertIn("a special character (e.g. !@#$...)", unmet)

    def test_empty_password_fails_all(self):
        self.assertEqual(len(password_requirements("")), 5)

    def test_seed_password_passes(self):
        self.assertEqual(password_requirements("Pams#Desk2026!"), [])


class TestUKMobileValidation(unittest.TestCase):
    def test_valid_mobile(self):
        self.assertTrue(is_valid_uk_mobile("07700900000"))

    def test_valid_mobile_with_spaces(self):
        self.assertTrue(is_valid_uk_mobile("077 009 00000"))

    def test_too_short(self):
        self.assertFalse(is_valid_uk_mobile("0770090000"))

    def test_too_long(self):
        self.assertFalse(is_valid_uk_mobile("077009000001"))

    def test_wrong_prefix(self):
        self.assertFalse(is_valid_uk_mobile("08700900000"))

    def test_empty_string(self):
        self.assertFalse(is_valid_uk_mobile(""))

    def test_normalize_strips_spaces(self):
        self.assertEqual(normalize_uk_mobile("  077 00 900 000  "), "07700900000")


if __name__ == "__main__":
    unittest.main()

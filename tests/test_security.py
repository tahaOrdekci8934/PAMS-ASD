"""
Security and RBAC tests for PAMS-ASD.
QA — Wayne Tong (24017066)

Covers (from test matrix):
  #25 - Login with correct credentials returns the matching user row
  #26 - Login with wrong password returns no user
  #27 - Login with an unknown email returns no user
  #28 - Each seeded staff account maps to the expected role
  #29 - Plaintext passwords are never stored — only SHA-256 digests
"""

import hashlib
import sqlite3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import hash_password

# ---------------------------------------------------------------------------
# Shared seed data — mirrors db_connection.initialize_db exactly so tests
# reflect what the live application inserts.
# ---------------------------------------------------------------------------

SEED_STAFF = [
    ("U001", "Sarah Mitchell",  "sarah.mitchell@paragon-pams.uk",  "Pams#Desk2026!",    "front_desk"),
    ("U002", "James Okonkwo",   "james.okonkwo@paragon-pams.uk",   "Pams#Finance2026!", "finance"),
    ("U003", "Priya Sharma",    "priya.sharma@paragon-pams.uk",    "Pams#Maint2026!",   "maintenance"),
    ("U004", "Marcus Webb",     "marcus.webb@paragon-pams.uk",     "Pams#Admin2026!",   "admin"),
    ("U005", "Elena Rossi",     "elena.rossi@paragon-pams.uk",     "Pams#Mgr2026!",     "manager"),
]


def _build_users_db() -> sqlite3.Connection:
    """Return an in-memory connection pre-populated with the seeded staff accounts."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE users (
            userID   TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role     TEXT NOT NULL
        )
    """)
    conn.executemany(
        "INSERT INTO users (userID, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
        [
            (uid, name, email, hash_password(plain), role)
            for uid, name, email, plain, role in SEED_STAFF
        ],
    )
    conn.commit()
    return conn


def _login(conn: sqlite3.Connection, email: str, password: str):
    """Replicate the credential lookup from LoginView.handle_login."""
    hashed = hash_password(password)
    return conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ?",
        (email, hashed),
    ).fetchone()

# Correct credentials return the matching user row

class TestLoginSuccess(unittest.TestCase):
    def setUp(self):
        self.conn = _build_users_db()

    def tearDown(self):
        self.conn.close()

    def test_correct_credentials_return_user(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Desk2026!")
        self.assertIsNotNone(user)

    def test_returned_user_has_correct_name(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Desk2026!")
        self.assertEqual(user["name"], "Sarah Mitchell")

    def test_returned_user_has_correct_id(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Desk2026!")
        self.assertEqual(user["userID"], "U001")

    def test_all_seed_accounts_can_log_in(self):
        for _, name, email, plain, _ in SEED_STAFF:
            with self.subTest(email=email):
                user = _login(self.conn, email, plain)
                self.assertIsNotNone(user, f"Login failed for {email}")
                self.assertEqual(user["name"], name)


# #26 — Wrong password returns no user
class TestLoginWrongPassword(unittest.TestCase):
    def setUp(self):
        self.conn = _build_users_db()

    def tearDown(self):
        self.conn.close()

    def test_wrong_password_returns_none(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "WrongPassword1!")
        self.assertIsNone(user)

    def test_empty_password_returns_none(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "")
        self.assertIsNone(user)

    def test_partial_password_returns_none(self):
        # Prefix of the real password must not authenticate.
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Desk")
        self.assertIsNone(user)

    def test_case_sensitive_password(self):
        # SHA-256 is case-sensitive; lowercase variant must fail.
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "pams#desk2026!")
        self.assertIsNone(user)

    def test_password_of_different_account_fails(self):
        # Cross-account password must not grant access.
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Finance2026!")
        self.assertIsNone(user)


# ---------------------------------------------------------------------------
# #27 — Unknown email returns no user
# ---------------------------------------------------------------------------

class TestLoginUnknownEmail(unittest.TestCase):
    def setUp(self):
        self.conn = _build_users_db()

    def tearDown(self):
        self.conn.close()

    def test_unknown_email_returns_none(self):
        user = _login(self.conn, "nobody@paragon-pams.uk", "Pams#Desk2026!")
        self.assertIsNone(user)

    def test_empty_email_returns_none(self):
        user = _login(self.conn, "", "Pams#Desk2026!")
        self.assertIsNone(user)

    def test_sql_injection_in_email_returns_none(self):
        # Classic OR-injection must not bypass the WHERE clause.
        user = _login(self.conn, "' OR '1'='1", "anything")
        self.assertIsNone(user)

    def test_sql_injection_in_password_returns_none(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "' OR '1'='1")
        self.assertIsNone(user)


#28 — Each seeded staff account maps to the expected role
class TestRoleAssignment(unittest.TestCase):
    def setUp(self):
        self.conn = _build_users_db()

    def tearDown(self):
        self.conn.close()

    def test_all_seed_roles_are_correct(self):
        for _, _, email, plain, expected_role in SEED_STAFF:
            with self.subTest(email=email):
                user = _login(self.conn, email, plain)
                self.assertIsNotNone(user)
                self.assertEqual(
                    user["role"],
                    expected_role,
                    f"{email} expected role '{expected_role}', got '{user['role']}'",
                )

    def test_front_desk_role(self):
        user = _login(self.conn, "sarah.mitchell@paragon-pams.uk", "Pams#Desk2026!")
        self.assertEqual(user["role"], "front_desk")

    def test_finance_role(self):
        user = _login(self.conn, "james.okonkwo@paragon-pams.uk", "Pams#Finance2026!")
        self.assertEqual(user["role"], "finance")

    def test_maintenance_role(self):
        user = _login(self.conn, "priya.sharma@paragon-pams.uk", "Pams#Maint2026!")
        self.assertEqual(user["role"], "maintenance")

    def test_admin_role(self):
        user = _login(self.conn, "marcus.webb@paragon-pams.uk", "Pams#Admin2026!")
        self.assertEqual(user["role"], "admin")

    def test_manager_role(self):
        user = _login(self.conn, "elena.rossi@paragon-pams.uk", "Pams#Mgr2026!")
        self.assertEqual(user["role"], "manager")

    def test_five_distinct_roles_exist(self):
        rows = self.conn.execute("SELECT DISTINCT role FROM users").fetchall()
        roles = {r["role"] for r in rows}
        self.assertEqual(roles, {"front_desk", "finance", "maintenance", "admin", "manager"})



#29 — Plaintext passwords are never stored; only SHA-256 digests persist

class TestPasswordStorage(unittest.TestCase):
    def setUp(self):
        self.conn = _build_users_db()

    def tearDown(self):
        self.conn.close()

    def test_stored_password_is_not_plaintext(self):
        for _, _, email, plain, _ in SEED_STAFF:
            with self.subTest(email=email):
                row = self.conn.execute(
                    "SELECT password FROM users WHERE email = ?", (email,)
                ).fetchone()
                self.assertNotEqual(
                    row["password"],
                    plain,
                    f"Plaintext password found in DB for {email}",
                )

    def test_stored_password_is_sha256_hex(self):
        for _, _, email, plain, _ in SEED_STAFF:
            with self.subTest(email=email):
                row = self.conn.execute(
                    "SELECT password FROM users WHERE email = ?", (email,)
                ).fetchone()
                expected = hashlib.sha256(plain.encode()).hexdigest()
                self.assertEqual(row["password"], expected)

    def test_stored_password_length_is_64(self):
        # SHA-256 hex digest is always 64 characters regardless of input length.
        rows = self.conn.execute("SELECT password FROM users").fetchall()
        for row in rows:
            self.assertEqual(len(row["password"]), 64)

    def test_stored_password_is_hexadecimal(self):
        rows = self.conn.execute("SELECT password FROM users").fetchall()
        for row in rows:
            try:
                int(row["password"], 16)
            except ValueError:
                self.fail(f"Stored password is not a valid hex string: {row['password']}")


if __name__ == "__main__":
    unittest.main()

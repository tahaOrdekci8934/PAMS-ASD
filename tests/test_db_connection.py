"""
Unit tests for database/db_connection.py
QA — Wayne Tong (24017066)
"""

import hashlib
import sqlite3
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db_connection import hash_password


class TestHashPassword(unittest.TestCase):
    def test_returns_sha256_hex(self):
        expected = hashlib.sha256("secret".encode()).hexdigest()
        self.assertEqual(hash_password("secret"), expected)

    def test_same_input_same_hash(self):
        self.assertEqual(hash_password("abc123"), hash_password("abc123"))

    def test_different_inputs_different_hashes(self):
        self.assertNotEqual(hash_password("PasswordA"), hash_password("PasswordB"))

    def test_hash_length_is_64(self):
        self.assertEqual(len(hash_password("anything")), 64)


EXPECTED_TABLES = {
    "users",
    "tenants",
    "apartments",
    "lease_agreements",
    "invoices",
    "maintenance_requests",
}


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            userID TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tenants (
            tenantID TEXT PRIMARY KEY,
            NINumber TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phoneNumber TEXT,
            email TEXT,
            occupation TEXT,
            references_ TEXT,
            apartmentRequirements TEXT
        );
        CREATE TABLE IF NOT EXISTS apartments (
            apartmentID TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            type TEXT,
            monthlyRent REAL,
            numberOfRooms INTEGER,
            occupancyStatus INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS lease_agreements (
            leaseID TEXT PRIMARY KEY,
            tenantID TEXT,
            apartmentID TEXT,
            startDate TEXT,
            endDate TEXT,
            depositAmount REAL,
            penaltyApplied REAL DEFAULT 0,
            lease_state TEXT NOT NULL DEFAULT 'ACTIVE',
            FOREIGN KEY (tenantID) REFERENCES tenants(tenantID),
            FOREIGN KEY (apartmentID) REFERENCES apartments(apartmentID)
        );
        CREATE TABLE IF NOT EXISTS invoices (
            invoiceID TEXT PRIMARY KEY,
            leaseID TEXT,
            amount REAL,
            dueDate TEXT,
            status TEXT DEFAULT 'UNPAID',
            FOREIGN KEY (leaseID) REFERENCES lease_agreements(leaseID)
        );
        CREATE TABLE IF NOT EXISTS maintenance_requests (
            requestID TEXT PRIMARY KEY,
            apartmentID TEXT,
            description TEXT,
            priority TEXT,
            status TEXT DEFAULT 'PENDING',
            dateReported TEXT,
            resolutionDate TEXT,
            timeTaken INTEGER,
            associatedCost REAL,
            FOREIGN KEY (apartmentID) REFERENCES apartments(apartmentID)
        );
    """)


class TestDBSchema(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        _create_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def _table_names(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return {r["name"] for r in rows}

    def test_all_tables_created(self):
        self.assertEqual(self._table_names(), EXPECTED_TABLES)

    def test_users_table_columns(self):
        info = self.conn.execute("PRAGMA table_info(users)").fetchall()
        cols = {r["name"] for r in info}
        self.assertSetEqual(cols, {"userID", "name", "email", "password", "role"})

    def test_lease_state_default_is_active(self):
        self.conn.execute(
            "INSERT INTO apartments VALUES ('A1','LOC','1-bed',1000,2,0)"
        )
        self.conn.execute(
            "INSERT INTO tenants VALUES ('T1','AB123456C','Alice','07700000000',"
            "'a@b.com','Job','Ref','Req')"
        )
        self.conn.execute(
            "INSERT INTO lease_agreements (leaseID, tenantID, apartmentID, startDate, endDate, depositAmount) "
            "VALUES ('L1','T1','A1','2026-01-01','2027-01-01',1200)"
        )
        row = self.conn.execute(
            "SELECT lease_state FROM lease_agreements WHERE leaseID='L1'"
        ).fetchone()
        self.assertEqual(row["lease_state"], "ACTIVE")

    def test_invoice_default_status_is_unpaid(self):
        self.conn.execute(
            "INSERT INTO apartments VALUES ('A2','LOC','1-bed',1000,2,0)"
        )
        self.conn.execute(
            "INSERT INTO tenants VALUES ('T2','AB654321D','Bob','07700000001',"
            "'b@b.com','Job','Ref','Req')"
        )
        self.conn.execute(
            "INSERT INTO lease_agreements (leaseID, tenantID, apartmentID, startDate, endDate, depositAmount) "
            "VALUES ('L2','T2','A2','2026-01-01','2027-01-01',1200)"
        )
        self.conn.execute(
            "INSERT INTO invoices (invoiceID, leaseID, amount, dueDate) "
            "VALUES ('I1','L2',1000,'2026-05-01')"
        )
        row = self.conn.execute(
            "SELECT status FROM invoices WHERE invoiceID='I1'"
        ).fetchone()
        self.assertEqual(row["status"], "UNPAID")

    def test_schema_is_idempotent(self):
        try:
            _create_schema(self.conn)
        except sqlite3.OperationalError as exc:
            self.fail(f"Schema re-run raised an error: {exc}")


if __name__ == "__main__":
    unittest.main()

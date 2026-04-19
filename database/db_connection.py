# Backend & Database — Finn Lennaghan (24024274) (SQLite schema, migrations, seed data, hashing, persistence).
# SQLite persistence for PAMS: schema, demonstration seed data, and seeded staff credentials.
import sqlite3
import os
import hashlib
import uuid
from datetime import date, timedelta

# Database file path co-located with this module for predictable resolution from the application.
DB_PATH = os.path.join(os.path.dirname(__file__), "pams.db")


def get_connection():
    # sqlite3.Row allows column access by name (for example row["email"]) in upper layers.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    # Returns the SHA-256 digest stored in the database; plaintext passwords are never persisted.
    return hashlib.sha256(password.encode()).hexdigest()


def initialize_db():
    # Application entry-point: create or upgrade schema, apply migrations, synchronise staff accounts, seed demonstration data.
    conn = get_connection()
    cursor = conn.cursor()

    # Core DDL in a single script; IF NOT EXISTS ensures idempotent execution on startup.
    cursor.executescript("""
        -- users: staff accounts (email + hashed password + role)
        CREATE TABLE IF NOT EXISTS users (
            userID TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        );

        -- tenants: resident tenants (distinct from staff users)
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

        -- apartments: rentable residential units
        CREATE TABLE IF NOT EXISTS apartments (
            apartmentID TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            type TEXT,
            monthlyRent REAL,
            numberOfRooms INTEGER,
            occupancyStatus INTEGER DEFAULT 0
        );

        -- lease_agreements: links tenant + flat + dates; lease_state = ACTIVE / LEAVING / ENDED
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

        -- invoices: bills for a lease (finance marks PAID / UNPAID)
        CREATE TABLE IF NOT EXISTS invoices (
            invoiceID TEXT PRIMARY KEY,
            leaseID TEXT,
            amount REAL,
            dueDate TEXT,
            status TEXT DEFAULT 'UNPAID',
            FOREIGN KEY (leaseID) REFERENCES lease_agreements(leaseID)
        );

        -- maintenance_requests: repair jobs tied to an apartment
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

    # Legacy databases may omit lease_state; add the column when absent.
    try:
        cursor.execute(
            "ALTER TABLE lease_agreements ADD COLUMN lease_state TEXT NOT NULL DEFAULT 'ACTIVE'"
        )
    except sqlite3.OperationalError:
        # Expected when the column already exists; suppress and continue.
        pass

    # Backend & Database — Finn Lennaghan (24024274): indexes for typical filters and joins (read-heavy admin / finance views).
    for index_sql in (
        "CREATE INDEX IF NOT EXISTS idx_apartments_location ON apartments(location)",
        "CREATE INDEX IF NOT EXISTS idx_apartments_occupancy ON apartments(occupancyStatus)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_lease ON invoices(leaseID)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_status_due ON invoices(status, dueDate)",
        "CREATE INDEX IF NOT EXISTS idx_lease_tenant ON lease_agreements(tenantID)",
        "CREATE INDEX IF NOT EXISTS idx_lease_apartment ON lease_agreements(apartmentID)",
        "CREATE INDEX IF NOT EXISTS idx_maint_apartment ON maintenance_requests(apartmentID)",
        "CREATE INDEX IF NOT EXISTS idx_maint_status ON maintenance_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    ):
        cursor.execute(index_sql)

    # Backend & Database — Finn Lennaghan (24024274): optional maintenance liaison columns (scheduled visit, tenant communication note).
    try:
        cursor.execute(
            "ALTER TABLE maintenance_requests ADD COLUMN scheduledVisitDate TEXT"
        )
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute(
            "ALTER TABLE maintenance_requests ADD COLUMN tenantCommunicationNote TEXT"
        )
    except sqlite3.OperationalError:
        pass

    # Past end date means the lease is finished; mark it ENDED if it was still ACTIVE or LEAVING.
    cursor.execute(
        """
        UPDATE lease_agreements
        SET lease_state = 'ENDED'
        WHERE date(endDate) < date('now')
          AND COALESCE(lease_state, 'ACTIVE') IN ('ACTIVE', 'LEAVING')
        """
    )

    # Five seeded staff accounts; refreshed on each initialisation so credentials match the distributed defaults.
    staff_accounts = [
        ("U001", "Sarah Mitchell", "sarah.mitchell@paragon-pams.uk", "Pams#Desk2026!", "front_desk"),
        ("U002", "James Okonkwo", "james.okonkwo@paragon-pams.uk", "Pams#Finance2026!", "finance"),
        ("U003", "Priya Sharma", "priya.sharma@paragon-pams.uk", "Pams#Maint2026!", "maintenance"),
        ("U004", "Marcus Webb", "marcus.webb@paragon-pams.uk", "Pams#Admin2026!", "admin"),
        ("U005", "Elena Rossi", "elena.rossi@paragon-pams.uk", "Pams#Mgr2026!", "manager"),
    ]
    # Hash plaintext passwords from the seed list prior to insertion.
    user_rows = [
        (uid, name, email, hash_password(plain), role)
        for uid, name, email, plain, role in staff_accounts
    ]
    # Collect identifiers for DELETE operations prior to re-inserting seed staff rows.
    staff_emails = tuple(email for _, _, email, _, _ in staff_accounts)
    staff_uids = tuple(uid for uid, _, _, _, _ in staff_accounts)
    # Remove existing seed rows, then insert current definitions to recover from inconsistent manual edits.
    _ph_e = ",".join("?" * len(staff_emails))
    cursor.execute(f"DELETE FROM users WHERE email IN ({_ph_e})", staff_emails)
    _ph_u = ",".join("?" * len(staff_uids))
    cursor.execute(f"DELETE FROM users WHERE userID IN ({_ph_u})", staff_uids)
    cursor.executemany(
        """
        INSERT INTO users (userID, name, email, password, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        user_rows,
    )

    # Runs when the apartments table is empty: insert demonstration flats, tenants, leases, invoices, and maintenance tickets.
    cursor.execute("SELECT COUNT(*) FROM apartments")
    apartments_count = cursor.fetchone()[0]

    if apartments_count == 0:
        # Construct apartment seed tuples from the per-city type, rent, and room configuration map.
        base_apartments = []
        for loc, (apt_type, rent, rooms) in {
            "BRISTOL": ("2-bedroom", 1250.0, 2),
            "CARDIFF": ("2-bedroom", 1125.0, 2),
            "LONDON": ("1-bedroom", 1800.0, 1),
            "MANCHESTER": ("2-bedroom", 1050.0, 2),
        }.items():
            # Primary flat per city.
            base_apartments.append((str(uuid.uuid4()), loc, apt_type, rent, rooms, 0))
            # Secondary flat with varied type and rent for richer filter and report samples.
            base_apartments.append((str(uuid.uuid4()), loc, "1-bedroom" if rooms == 2 else "studio", rent * 0.78, 1, 0))

        # occupancyStatus 0 indicates vacant stock prior to tenant assignment in the seeding block below.
        cursor.executemany(
            """
            INSERT INTO apartments (apartmentID, location, type, monthlyRent, numberOfRooms, occupancyStatus)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            base_apartments,
        )

    cursor.execute("SELECT COUNT(*) FROM tenants")
    tenants_count = cursor.fetchone()[0]
    today = date.today()

    if tenants_count == 0:
        # Index apartments by city to select one unit per location for seeded leases.
        cursor.execute("SELECT apartmentID, location, monthlyRent FROM apartments")
        apt_rows = cursor.fetchall()
        by_loc = {}
        for r in apt_rows:
            by_loc.setdefault(r["location"], []).append(r)

        # One seeded tenant per city, each with an active lease, one paid invoice, and one overdue unpaid invoice.
        last_letters = ["C", "D", "E", "F"]
        locations = ["BRISTOL", "CARDIFF", "LONDON", "MANCHESTER"]

        for i, loc in enumerate(locations):
            # Skip cities with no apartment rows (defensive guard).
            if loc not in by_loc or not by_loc[loc]:
                continue
            apt = by_loc[loc][0]
            apartment_id = apt["apartmentID"]
            monthly_rent = float(apt["monthlyRent"] or 0)

            # Generate UUID primary keys for tenant, lease, and invoice entities.
            tenant_id = str(uuid.uuid4())
            lease_id = str(uuid.uuid4())
            invoice_paid_id = str(uuid.uuid4())
            invoice_unpaid_id = str(uuid.uuid4())

            # Synthetic but unique National Insurance numbers for seeded tenants.
            nin = f"AB{100000 + i:06d}{last_letters[i % len(last_letters)]}"
            name = f"Tenant {loc.title()}"
            phone = f"07700{i}99000"  # demonstration telephone format (not subject to live validation rules)
            email = f"tenant.{loc.lower()}@paragon-pams.uk"
            occupation = "Analyst"
            references = "John Smith, 07000000000"
            apt_req = f"Preferred: {loc}, near amenities"

            start_date = today.isoformat()
            end_date = (today + timedelta(days=365)).isoformat()
            deposit = 1200.0

            cursor.execute(
                """
                INSERT INTO tenants (tenantID, NINumber, name, phoneNumber, email,
                                      occupation, references_, apartmentRequirements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, nin, name, phone, email, occupation, references, apt_req),
            )

            cursor.execute(
                """
                INSERT INTO lease_agreements
                    (leaseID, tenantID, apartmentID, startDate, endDate, depositAmount, lease_state)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                """,
                (lease_id, tenant_id, apartment_id, start_date, end_date, deposit),
            )

            # Mark the apartment occupied after inserting the active lease.
            cursor.execute(
                "UPDATE apartments SET occupancyStatus = 1 WHERE apartmentID = ?",
                (apartment_id,),
            )

            # Paid invoice with historical due date (not classified as late in the user interface).
            cursor.execute(
                """
                INSERT INTO invoices (invoiceID, leaseID, amount, dueDate, status)
                VALUES (?, ?, ?, ?, 'PAID')
                """,
                (invoice_paid_id, lease_id, monthly_rent, (today - timedelta(days=60)).isoformat()),
            )
            # Unpaid invoice with due date in the past to populate late-payment scenarios in finance views.
            cursor.execute(
                """
                INSERT INTO invoices (invoiceID, leaseID, amount, dueDate, status)
                VALUES (?, ?, ?, ?, 'UNPAID')
                """,
                (invoice_unpaid_id, lease_id, monthly_rent, (today - timedelta(days=10)).isoformat()),
            )

        # Sample maintenance requests spanning pending, in-progress, and resolved states.
        cursor.execute("SELECT apartmentID FROM apartments")
        all_apt_ids = [r["apartmentID"] for r in cursor.fetchall()]
        if all_apt_ids:
            # Tuple order: status, description, priority, apartment identifier, reported date.
            request_specs = [
                ("PENDING", "Leaking tap in kitchen", "HIGH", all_apt_ids[0], (today - timedelta(days=4)).isoformat()),
                ("IN_PROGRESS", "Blocked sink - persistent water", "MEDIUM", all_apt_ids[1 if len(all_apt_ids) > 1 else 0], (today - timedelta(days=7)).isoformat()),
                (
                    "RESOLVED",
                    "Replace faulty light fixture",
                    "LOW",
                    all_apt_ids[2 if len(all_apt_ids) > 2 else 0],
                    (today - timedelta(days=12)).isoformat(),
                ),
            ]

            for idx, spec in enumerate(request_specs):
                status, desc, priority, apartment_id, date_reported = spec
                request_id = str(uuid.uuid4())
                # Resolved tickets include resolution metadata; other statuses leave those columns null.
                res_date = None
                time_taken = None
                cost = None
                if status == "RESOLVED":
                    res_date = (today - timedelta(days=2)).isoformat()
                    time_taken = 90
                    cost = 300.0

                cursor.execute(
                    """
                    INSERT INTO maintenance_requests
                        (requestID, apartmentID, description, priority, status, dateReported, resolutionDate, timeTaken, associatedCost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        apartment_id,
                        desc,
                        priority,
                        status,
                        date_reported,
                        res_date,
                        time_taken,
                        cost,
                    ),
                )

    # Commit transactions and close the connection so the client application can open subsequent connections.
    conn.commit()
    conn.close()
    print("Database ready.")

# QA — Wayne Tong (24017066)
# Execute: python database/db_connection.py from the project root, or python db_connection.py from the database directory.
if __name__ == "__main__":
    initialize_db()
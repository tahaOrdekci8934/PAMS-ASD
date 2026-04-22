## Paragon Apartment Management System (PAMS)

Desktop application for Paragon-style apartment operations: tenants, leases, apartments, invoicing, and maintenance. Built with Python 3, PyQt5, and SQLite for local persistence. Includes seeded staff accounts and demo data for evaluation and local testing.

Prerequisites
Python 3.10 or newer (3.12+ recommended)
pip and a virtual environment (recommended)

Dependencies are listed in requirements.txt (currently PyQt5 ≥ 5.15). All other imports are from the Python standard library.

Setup
Clone or extract the project, then from the repository root (directory containing main.py):


python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt


A pre-generated pip_list.txt is included in the submission ZIP as per assessment requirements.

Run
Always start the app from the project root so package imports resolve:


python main.py


On first run, initialize_db() creates or updates database/pams.db, applies schema migrations, refreshes seeded staff password hashes, and inserts demo apartments, tenants, leases, invoices, and sample maintenance rows when the database is empty.


Demo accounts
After at least one successful launch, sign in with (email is matched case-insensitively):

| Role         | Email                             | Password           |
|-------------|-----------------------------------|--------------------|
| Front desk  | sarah.mitchell@paragon-pams.uk    | Pams#Desk2026!     |
| Finance     | james.okonkwo@paragon-pams.uk     | Pams#Finance2026!  |
| Maintenance | priya.sharma@paragon-pams.uk      | Pams#Maint2026!    |
| Admin       | marcus.webb@paragon-pams.uk       | Pams#Admin2026!    |
| Manager     | elena.rossi@paragon-pams.uk       | Pams#Mgr2026!      |

Automatic Tests
From the project root (the folder that contains main.py and tests/):

python -m unittest tests.test_form_validators -v
python -m unittest tests.test_hash_password -v

The first module covers shared validators (email, password policy, UK mobile helpers) used by login and forms. The second checks that hash_password produces the expected SHA-256 hex digests for stored staff credentials.

Database maintenance (no GUI)
From the project root:


python database/db_connection.py


If apartments and tenants already contain data, this reapplies migrations and refreshes the five seeded staff users; it does not clear tenant or billing data. Full demo seeding of flats and tenants runs only when those tables are empty.

SQLite dump (submission)
sqlite3 database/pams.db .dump > database/pams_dump.sql


Our zip includes database/pams_dump.sql (from the command above) and database/pams.db. Copy both into database/ in this repo and run python main.py. 

Project layout
| Path | Role |
|------|------|
| main.py | Entry point |
| requirements.txt | Third-party dependencies |
| .gitignore | Ignores venv/, __pycache__/, local database/pams.db, IDE metadata |
| database/ | SQLite access, schema, migrations, seeding (db_connection.py) |
| views/ | PyQt5 UI: login, shell, sidebar, role panels |
| tests/ | Unit tests (unittest) |

Imports assume database/ remains a package (e.g. from database.db_connection import …). Moving db_connection.py to the repository root without updating imports will break the application.

Troubleshooting
| Symptom | Likely fix |
|---------|------------|
| ModuleNotFoundError: No module named 'database' | Run from project root, not from views/ or database/. |
| No module named 'PyQt5' | Activate the venv and run pip install -r requirements.txt. |
| Demo login fails | Run the app once so initialize_db() can refresh user rows and hashes. |
| Tables show old data | Switch sidebar tabs or use panel refresh actions where available. |

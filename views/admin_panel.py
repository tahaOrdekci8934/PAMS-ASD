# UI/UX & Frontend — Taha Ordekci (25013992) (admin PyQt screens: users, apartments, lease table).
# Admin: create staff users, manage flats, view leases (incl. ACTIVE / LEAVING / ENDED).
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QComboBox, QMessageBox, QHeaderView,
                              QStackedWidget, QFormLayout, QDialog, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from database.db_connection import get_connection, hash_password
from views.form_validators import is_valid_email, password_requirements
from views import app_theme
import sqlite3
import uuid


class AdminPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        # Initial assigned office; superseded once locations are loaded from the database.
        self.assigned_location = "BRISTOL"

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        # Agile PM & Security — Dylan Morgan (24030018): administrative apartment and lease data are scoped to one office location at a time per assignment requirements.
        scope_card = QFrame()
        scope_card.setObjectName("FormCard")
        scope_layout = QVBoxLayout(scope_card)
        scope_layout.setContentsMargins(16, 14, 16, 14)
        scope_layout.setSpacing(8)
        scope_row = QHBoxLayout()
        scope_lbl = QLabel("Assigned office location (apartments & leases data scope):")
        scope_lbl.setStyleSheet(app_theme.FIELD_LABEL + " background: transparent;")
        self.admin_scope_combo = QComboBox()
        self.admin_scope_combo.setMinimumWidth(200)
        self.admin_scope_combo.currentTextChanged.connect(self._on_admin_assigned_location_changed)
        scope_row.addWidget(scope_lbl)
        scope_row.addWidget(self.admin_scope_combo)
        scope_row.addStretch()
        scope_policy = QLabel(
            "Switch this dropdown to the Paragon city you are administering. "
            "Apartments and leases are always filtered to that city. "
            "Staff accounts remain organisation-wide."
        )
        scope_policy.setWordWrap(True)
        scope_policy.setStyleSheet(app_theme.HINT + " background: transparent;")
        scope_layout.addLayout(scope_row)
        scope_layout.addWidget(scope_policy)

        self._populate_admin_scope_combo()

        # QStackedWidget indexes: 0 users, 1 apartments, 2 leases (sidebar order).
        self.stack = QStackedWidget()

        self.user_widget = self.build_user_management()
        self.apartment_widget = self.build_apartment_management()
        self.leases_widget = self.build_leases_management()

        self.stack.addWidget(self.user_widget)
        self.stack.addWidget(self.apartment_widget)
        self.stack.addWidget(self.leases_widget)

        root.addWidget(scope_card)
        root.addWidget(self.stack)
        self.setLayout(root)

    def show_users(self):
        # Sidebar index 0: display the user-management page and reload staff accounts.
        self.stack.setCurrentIndex(0)
        self.load_users()

    def show_apartments(self):
        self.stack.setCurrentIndex(1)
        self.load_apartments()

    def show_leases(self):
        self.stack.setCurrentIndex(2)
        self.load_leases()

    def _require_admin(self):
        # Agile PM & Security — Dylan Morgan (24030018): deny access when this panel is not loaded for an administrator role.
        if self.user.get("role") != "admin":
            QMessageBox.critical(
                self,
                "Access denied",
                "Only administrators may use this panel.",
            )
            return False
        return True

    def _populate_admin_scope_combo(self):
        self.admin_scope_combo.blockSignals(True)
        self.admin_scope_combo.clear()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM apartments ORDER BY location")
        locs = [r["location"] for r in cursor.fetchall() if r["location"]]
        conn.close()
        if not locs:
            locs = ["BRISTOL", "CARDIFF", "LONDON", "MANCHESTER"]
        for loc in locs:
            self.admin_scope_combo.addItem(loc)
        self.admin_scope_combo.blockSignals(False)
        if self.admin_scope_combo.count():
            self.assigned_location = self.admin_scope_combo.currentText()

    def _on_admin_assigned_location_changed(self, text):
        if not text:
            return
        self.assigned_location = text
        self._sync_apartment_location_field()
        if hasattr(self, "apt_table"):
            self.load_apartments()
        if hasattr(self, "lease_scope_label"):
            self._refresh_lease_scope_banner()
            self.load_leases()

    def _sync_apartment_location_field(self):
        if not hasattr(self, "a_location"):
            return
        self.a_location.blockSignals(True)
        self.a_location.clear()
        self.a_location.addItem(self.assigned_location)
        self.a_location.setEnabled(False)
        self.a_location.blockSignals(False)

    # --- Page 1: staff user administration (add and delete; tenant records are out of scope here) ---

    def build_user_management(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("User Management")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        # Horizontal form row: name, email, password, role selector, add action.
        form_layout = QHBoxLayout()
        self.u_name = QLineEdit(); self.u_name.setPlaceholderText("Full Name")
        self.u_email = QLineEdit(); self.u_email.setPlaceholderText("Email")
        self.u_pass = QLineEdit(); self.u_pass.setPlaceholderText("Password")
        self.u_pass.setEchoMode(QLineEdit.Password)
        self.u_role = QComboBox()
        self.u_role.addItems(["front_desk", "finance", "maintenance", "admin", "manager"])

        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)

        for w in [self.u_name, self.u_email, self.u_pass, self.u_role, add_btn]:
            form_layout.addWidget(w)

        hint_email = QLabel("Email must look like name@domain.com (include '@').")
        hint_email.setWordWrap(True)
        hint_email.setStyleSheet(app_theme.HINT + "background: transparent;")

        hint_pass = QLabel(
            "Password rules for new users: at least 8 characters, include uppercase, lowercase, "
            "a number, and a special character (e.g. !@#$)."
        )
        hint_pass.setWordWrap(True)
        hint_pass.setStyleSheet(app_theme.HINT + "background: transparent;")

        # Read-only table with per-row delete control in the final column.
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(4)
        self.user_table.setHorizontalHeaderLabels(["Name", "Email", "Role", "Action"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.user_table.verticalHeader().setVisible(False)

        self.users_empty_hint = QLabel(
            "No staff users are registered yet. Use the form above to add an account."
        )
        self.users_empty_hint.setWordWrap(True)
        self.users_empty_hint.setStyleSheet(app_theme.HINT + " background: transparent;")
        self.users_empty_hint.setVisible(False)

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(hint_email)
        layout.addWidget(hint_pass)
        layout.addWidget(self.user_table)
        layout.addWidget(self.users_empty_hint)
        widget.setLayout(layout)

        self.load_users()
        return widget

    def load_users(self):
        # Always query the database so the table reflects the latest inserts and deletions.
        if not self._require_admin():
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT userID, name, email, role FROM users")
        users = cursor.fetchall()
        conn.close()

        self.users_empty_hint.setVisible(len(users) == 0)
        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            # Standard text columns use QTableWidgetItem instances.
            self.user_table.setItem(row, 0, QTableWidgetItem(user["name"]))
            self.user_table.setItem(row, 1, QTableWidgetItem(user["email"]))
            self.user_table.setItem(row, 2, QTableWidgetItem(user["role"]))

            # Default argument binds userID per iteration to avoid late-binding closure over the loop variable.
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                f"background-color: {app_theme.C_DANGER}; color: {app_theme.C_ON_ACCENT}; "
                f"border-radius: 6px; padding: 6px 12px; font-weight: 600;"
            )
            del_btn.clicked.connect(lambda _, uid=user["userID"]: self.delete_user(uid))
            self.user_table.setCellWidget(row, 3, del_btn)

    def add_user(self):
        if not self._require_admin():
            return
        # Normalise email to lowercase for consistency with the login lookup logic.
        name = self.u_name.text().strip()
        email = self.u_email.text().strip().lower()
        password = self.u_pass.text().strip()
        role = self.u_role.currentText()

        if not name or not email or not password:
            QMessageBox.warning(
                self,
                "Missing information",
                "Please complete all fields before adding a user.",
            )
            return

        if not is_valid_email(email):
            QMessageBox.warning(
                self,
                "Invalid email",
                "Please enter a valid email address (it must include '@', e.g. name@example.com).",
            )
            return

        unmet = password_requirements(password)
        if unmet:
            QMessageBox.warning(
                self,
                "Password requirements",
                "The password does not meet the security requirements. Please include:\n- "
                + "\n- ".join(unmet),
            )
            return

        # Primary key uses a UUID string; password stored as an SHA-256 hash consistent with authentication.
        conn = get_connection()
        cursor = conn.cursor()
        # Backend & Database — Finn Lennaghan (24024274): insert new staff user (hashed password, unique email).
        try:
            cursor.execute(
                "INSERT INTO users (userID, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), name, email, hash_password(password), role)
            )
            conn.commit()
            QMessageBox.information(self, "User added", f"User '{name}' has been added successfully.")
            self.u_name.clear(); self.u_email.clear(); self.u_pass.clear()
            self.load_users()
        except sqlite3.IntegrityError:
            # Map duplicate-email constraint violations to a clear user-facing warning.
            QMessageBox.warning(
                self,
                "Duplicate email",
                "A staff user with this email address already exists.",
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Unable to add user",
                f"The user could not be created. Details:\n{e}",
            )
        finally:
            conn.close()

    def delete_user(self, user_id):
        if not self._require_admin():
            return
        if self.user.get("userID") == user_id:
            QMessageBox.warning(
                self,
                "Not allowed",
                "You cannot delete the administrator account you are currently signed in with.",
            )
            return
        # Require explicit confirmation before deleting a staff user record.
        reply = QMessageBox.question(
            self,
            "Confirm deletion",
            "Are you sure you want to delete this user? This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            conn = get_connection()
            # Backend & Database — Finn Lennaghan (24024274): remove staff user row.
            conn.execute("DELETE FROM users WHERE userID = ?", (user_id,))
            conn.commit()
            conn.close()
            self.load_users()

    # --- Page 2: apartment inventory for the assigned office ---

    def build_apartment_management(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Apartment Management")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        # Location is locked to the administrator's assigned office (see scope banner above).
        form_layout = QHBoxLayout()
        self.a_location = QComboBox()
        self.a_type = QLineEdit(); self.a_type.setPlaceholderText("Type (e.g. 2-bedroom)")
        self.a_rent = QLineEdit(); self.a_rent.setPlaceholderText("Monthly Rent (£)")
        self.a_rooms = QLineEdit(); self.a_rooms.setPlaceholderText("Number of Rooms")

        add_btn = QPushButton("Add Apartment")
        add_btn.clicked.connect(self.add_apartment)

        for w in [self.a_location, self.a_type, self.a_rent, self.a_rooms, add_btn]:
            form_layout.addWidget(w)

        self.apt_table = QTableWidget()
        self.apt_table.setColumnCount(5)
        self.apt_table.setHorizontalHeaderLabels(["Location", "Type", "Rent (£)", "Rooms", "Status"])
        self.apt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.apt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.apt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.apt_table.verticalHeader().setVisible(False)

        self.apts_empty_hint = QLabel(
            "No apartments exist for the selected office yet. Add one with the form above."
        )
        self.apts_empty_hint.setWordWrap(True)
        self.apts_empty_hint.setStyleSheet(app_theme.HINT + " background: transparent;")
        self.apts_empty_hint.setVisible(False)

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addWidget(self.apt_table)
        layout.addWidget(self.apts_empty_hint)
        widget.setLayout(layout)

        self._sync_apartment_location_field()
        self.load_apartments()
        return widget

    def load_apartments(self):
        # occupancyStatus 0 renders as Available, 1 as Occupied (consistent with manager reporting).
        if not self._require_admin():
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM apartments WHERE location = ? ORDER BY type, monthlyRent",
            (self.assigned_location,),
        )
        apts = cursor.fetchall()
        conn.close()

        self.apts_empty_hint.setVisible(len(apts) == 0)
        self.apt_table.setRowCount(len(apts))
        for row, apt in enumerate(apts):
            self.apt_table.setItem(row, 0, QTableWidgetItem(apt["location"]))
            self.apt_table.setItem(row, 1, QTableWidgetItem(apt["type"] or ""))
            self.apt_table.setItem(row, 2, QTableWidgetItem(str(apt["monthlyRent"])))
            self.apt_table.setItem(row, 3, QTableWidgetItem(str(apt["numberOfRooms"])))
            status = "Occupied" if apt["occupancyStatus"] else "Available"
            self.apt_table.setItem(row, 4, QTableWidgetItem(status))

    def add_apartment(self):
        if not self._require_admin():
            return
        # Rent and rooms must convert to number types before INSERT.
        location = self.a_location.currentText()
        apt_type = self.a_type.text().strip()
        rent_text = self.a_rent.text().strip()
        rooms_text = self.a_rooms.text().strip()

        if not apt_type or not rent_text or not rooms_text:
            QMessageBox.warning(
                self,
                "Missing information",
                "Please complete all apartment fields before saving.",
            )
            return

        try:
            rent = float(rent_text)
            rooms = int(rooms_text)
        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid input",
                "Monthly rent must be a valid number, and the number of rooms must be a whole number.",
            )
            return

        if location != self.assigned_location:
            QMessageBox.warning(
                self,
                "Location mismatch",
                "New apartments must be created under your currently assigned office location.",
            )
            return

        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): insert new apartment record.
        try:
            conn.execute(
                "INSERT INTO apartments (apartmentID, location, type, monthlyRent, numberOfRooms) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), location, apt_type, rent, rooms)
            )
            conn.commit()
            QMessageBox.information(self, "Apartment added", "The apartment has been added successfully.")
            self.a_type.clear(); self.a_rent.clear(); self.a_rooms.clear()
            self.load_apartments()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Unable to add apartment",
                f"The apartment could not be saved. Details:\n{e}",
            )
        finally:
            conn.close()

    # --- Page 3: read-only lease register scoped to the assigned office ---

    def build_leases_management(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Lease Agreements")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        filter_row = QHBoxLayout()
        self.lease_scope_label = QLabel()
        self.lease_scope_label.setWordWrap(True)
        self.lease_scope_label.setStyleSheet(app_theme.HINT + " background: transparent;")
        filter_row.addWidget(self.lease_scope_label, 1)

        self.leases_table = QTableWidget()
        self.leases_table.setColumnCount(7)
        self.leases_table.setHorizontalHeaderLabels(
            ["Lease ID", "Tenant", "Apartment", "Start", "End", "Deposit (£)", "Status"]
        )
        self.leases_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.leases_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.leases_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.leases_table.verticalHeader().setVisible(False)
        self.leases_table.setMinimumHeight(320)

        self.leases_empty_hint = QLabel(
            "No lease agreements are recorded for the selected office yet."
        )
        self.leases_empty_hint.setWordWrap(True)
        self.leases_empty_hint.setStyleSheet(app_theme.HINT + " background: transparent;")
        self.leases_empty_hint.setVisible(False)

        layout.addWidget(title)
        layout.addLayout(filter_row)
        layout.addWidget(self.leases_table)
        layout.addWidget(self.leases_empty_hint)
        widget.setLayout(layout)

        self._refresh_lease_scope_banner()
        self.load_leases()
        return widget

    def _refresh_lease_scope_banner(self):
        self.lease_scope_label.setText(
            f"Showing lease agreements for {self.assigned_location} "
            "(matches the assigned office banner above)."
        )

    def load_leases(self):
        # Backend & Database — Finn Lennaghan (24024274): joined lease list with computed status for admin view.
        if not self._require_admin():
            return
        location_value = self.assigned_location

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                la.leaseID,
                t.name AS tenantName,
                a.location || ' - ' || COALESCE(a.type,'') AS apartment,
                la.startDate,
                la.endDate,
                la.depositAmount,
                CASE
                    WHEN COALESCE(la.lease_state, 'ACTIVE') = 'LEAVING' THEN 'LEAVING'
                    WHEN date(la.endDate) >= date('now') THEN 'ACTIVE'
                    ELSE 'ENDED'
                END AS leaseStatus
            FROM lease_agreements la
            JOIN tenants t ON t.tenantID = la.tenantID
            JOIN apartments a ON a.apartmentID = la.apartmentID
            WHERE a.location = ?
            ORDER BY date(la.endDate) ASC
            """,
            (location_value,),
        )
        rows = cursor.fetchall()
        conn.close()

        # SQL CASE expression: LEAVING takes precedence; otherwise ACTIVE or ENDED based on calendar end date.
        self.leases_empty_hint.setVisible(len(rows) == 0)
        self.leases_table.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            self.leases_table.setItem(idx, 0, QTableWidgetItem(str(r["leaseID"])))
            self.leases_table.setItem(idx, 1, QTableWidgetItem(r["tenantName"] or ""))
            self.leases_table.setItem(idx, 2, QTableWidgetItem(r["apartment"] or ""))
            self.leases_table.setItem(idx, 3, QTableWidgetItem(r["startDate"] or ""))
            self.leases_table.setItem(idx, 4, QTableWidgetItem(r["endDate"] or ""))
            self.leases_table.setItem(idx, 5, QTableWidgetItem(f"{float(r['depositAmount'] or 0):.2f}"))
            st_item = QTableWidgetItem(r["leaseStatus"] or "")
            # Status column uses colour emphasis for LEAVING and ACTIVE lease states.
            if (r["leaseStatus"] or "") == "LEAVING":
                st_item.setForeground(QColor(app_theme.C_WARNING))
            elif (r["leaseStatus"] or "") == "ACTIVE":
                st_item.setForeground(QColor(app_theme.C_SUCCESS))
            self.leases_table.setItem(idx, 6, st_item)
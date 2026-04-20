# UI/UX & Frontend — Taha Ordekci (25013992) (front desk PyQt: tenant form, tables, maintenance tab, dialogs).
# Front desk: register tenants, leases, maintenance; early exit and delete tenant flows.
# Uses SQLite through get_connection() and shares validators with login/admin.
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QLineEdit, QComboBox, QMessageBox, QHeaderView,
                              QStackedWidget, QFormLayout, QDateEdit, QTextEdit,
                              QDialog, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
                              QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor
from database.db_connection import get_connection
import uuid
from datetime import date, timedelta
from views.form_validators import (
    is_valid_email,
    is_valid_uk_mobile,
    normalize_uk_mobile,
    attach_uk_mobile_input,
    uk_mobile_format_hint,
)
from views import app_theme


class FrontDeskPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        # QStackedWidget switches between tenant registration and maintenance request pages.
        self.stack = QStackedWidget()

        self.tenant_widget = self.build_tenant_panel()
        self.maintenance_widget = self.build_maintenance_panel()

        self.stack.addWidget(self.tenant_widget)
        self.stack.addWidget(self.maintenance_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def show_tenants(self):
        # Sidebar tab 0: show tenant registration and reload the tenant grid.
        self.stack.setCurrentIndex(0)
        self.load_tenants()

    def show_maintenance(self):
        # Sidebar tab 1: show maintenance intake and refresh apartment and request data.
        self.stack.setCurrentIndex(1)
        self._load_all_apartments_for_maintenance()
        self.load_maintenance_requests()

    # --- Page 1: tenant registration form, directory table, and per-row administrative actions ---

    def build_tenant_panel(self):
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        # Page title using shared stylesheet tokens for visual consistency.
        title = QLabel("Tenant Registration")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        # --- Registration form ---
        form_frame = QFrame()
        form_frame.setObjectName("FormCard")
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(10)

        form_lbl = QLabel("Register New Tenant")
        form_lbl.setStyleSheet(app_theme.SECTION_TITLE + "font-size: 14px; background: transparent;")
        form_layout.addWidget(form_lbl)

        # Row 1: personal identifiers and contact fields.
        row1 = QHBoxLayout()
        self.t_name = QLineEdit(); self.t_name.setPlaceholderText("Full Name *")
        self.t_ni = QLineEdit(); self.t_ni.setPlaceholderText("NI Number * (e.g. AB123456C)")
        self.t_phone = QLineEdit()
        self.t_phone.setPlaceholderText("07545798234")
        attach_uk_mobile_input(self.t_phone)
        self.t_email = QLineEdit(); self.t_email.setPlaceholderText("Email Address")
        for w in [self.t_name, self.t_ni, self.t_phone, self.t_email]:
            row1.addWidget(w)
        form_layout.addLayout(row1)

        phone_hint = QLabel(uk_mobile_format_hint())
        phone_hint.setWordWrap(True)
        phone_hint.setStyleSheet(app_theme.HINT + "background: transparent;")
        form_layout.addWidget(phone_hint)

        email_hint = QLabel(
            "Email is required and must be valid (include '@', e.g. tenant@email.com)."
        )
        email_hint.setWordWrap(True)
        email_hint.setStyleSheet(app_theme.HINT + "background: transparent;")
        form_layout.addWidget(email_hint)

        # Row 2: employment and reference information.
        row2 = QHBoxLayout()
        self.t_occupation = QLineEdit(); self.t_occupation.setPlaceholderText("Occupation")
        self.t_references = QLineEdit(); self.t_references.setPlaceholderText("References (e.g. John Smith, 07700900000)")
        row2.addWidget(self.t_occupation)
        row2.addWidget(self.t_references)
        form_layout.addLayout(row2)

        # Row 3: apartment requirements and optional lease assignment.
        row3 = QHBoxLayout()
        self.t_apt_req = QLineEdit(); self.t_apt_req.setPlaceholderText("Apartment Requirements (e.g. 2-bedroom, Bristol)")

        apt_lbl = QLabel("Assign Apartment:")
        apt_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.t_apt_combo = QComboBox()
        self._load_available_apartments()

        row3.addWidget(self.t_apt_req)
        row3.addWidget(apt_lbl)
        row3.addWidget(self.t_apt_combo)
        form_layout.addLayout(row3)

        # Row 4: lease calendar range and deposit amount.
        row4 = QHBoxLayout()

        start_lbl = QLabel("Lease Start:")
        start_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.t_start_date = QDateEdit()
        self.t_start_date.setCalendarPopup(True)
        self.t_start_date.setDate(QDate.currentDate())

        end_lbl = QLabel("Lease End:")
        end_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.t_end_date = QDateEdit()
        self.t_end_date.setCalendarPopup(True)
        self.t_end_date.setDate(QDate.currentDate().addYears(1))

        # Synchronise start and end dates so the lease interval remains at least one day in length.
        self.t_start_date.dateChanged.connect(self._tenant_lease_start_changed)
        self.t_end_date.dateChanged.connect(self._tenant_lease_end_changed)
        self._tenant_lease_start_changed()
        self._tenant_lease_end_changed()

        lease_date_hint = QLabel(
            "Lease end must be at least one day after the start date (the calendar will adjust if needed)."
        )
        lease_date_hint.setWordWrap(True)
        lease_date_hint.setStyleSheet(app_theme.HINT + "background: transparent;")

        deposit_lbl = QLabel("Deposit (£):")
        deposit_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.t_deposit = QDoubleSpinBox()
        self.t_deposit.setRange(0, 99999)
        self.t_deposit.setValue(1200)
        self.t_deposit.setPrefix("£ ")

        row4.addWidget(start_lbl)
        row4.addWidget(self.t_start_date)
        row4.addWidget(end_lbl)
        row4.addWidget(self.t_end_date)
        row4.addWidget(deposit_lbl)
        row4.addWidget(self.t_deposit)
        form_layout.addLayout(row4)
        form_layout.addWidget(lease_date_hint)

        # Primary registration action.
        btn_row = QHBoxLayout()
        reg_btn = QPushButton("Register Tenant")
        reg_btn.setFixedWidth(180)
        reg_btn.clicked.connect(self.register_tenant)
        btn_row.addStretch()
        btn_row.addWidget(reg_btn)
        form_layout.addLayout(btn_row)

        form_frame.setLayout(form_layout)

        # --- Tenant directory table ---
        table_lbl = QLabel("Registered Tenants")
        table_lbl.setStyleSheet(app_theme.SECTION_TITLE + "font-size: 14px; background: transparent;")

        self.tenant_table = QTableWidget()
        self.tenant_table.setColumnCount(7)
        self.tenant_table.setHorizontalHeaderLabels([
            "Name", "NI Number", "Phone", "Email", "Occupation", "Apartment", "Actions"
        ])
        tenant_hdr = self.tenant_table.horizontalHeader()
        # Stretch text columns; reserve the actions column for multiple buttons without equal-width stretch.
        for col in range(6):
            tenant_hdr.setSectionResizeMode(col, QHeaderView.Stretch)
        tenant_hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.tenant_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tenant_table.setSelectionBehavior(QTableWidget.SelectRows)
        vh = self.tenant_table.verticalHeader()
        vh.setVisible(False)
        # Increased default row height so embedded action buttons are not clipped vertically.
        vh.setDefaultSectionSize(52)
        vh.setMinimumSectionSize(48)
        self.tenant_table.setMinimumHeight(250)

        outer.addWidget(title)
        outer.addWidget(form_frame)
        outer.addWidget(table_lbl)
        outer.addWidget(self.tenant_table)
        container.setLayout(outer)

        self.load_tenants()
        return container

    def _load_available_apartments(self):
        # Apartment assignment list restricted to vacant units (occupancyStatus = 0).
        self.t_apt_combo.clear()
        self.t_apt_combo.addItem("-- No Assignment --", None)
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT apartmentID, location, type, monthlyRent FROM apartments WHERE occupancyStatus = 0"
        )
        for apt in cursor.fetchall():
            label = f"{apt['location']} | {apt['type'] or 'N/A'} | £{apt['monthlyRent']}/mo"
            self.t_apt_combo.addItem(label, apt['apartmentID'])
        conn.close()

    def load_tenants(self):
        conn = get_connection()
        cursor = conn.cursor()
        # Backend & Database — Finn Lennaghan (24024274): keep lease_state consistent with calendar dates before SELECT.
        # Aligns with database initialisation: past end dates transition ACTIVE or LEAVING leases to ENDED.
        cursor.execute(
            """
            UPDATE lease_agreements
            SET lease_state = 'ENDED'
            WHERE date(endDate) < date('now')
              AND COALESCE(lease_state, 'ACTIVE') IN ('ACTIVE', 'LEAVING')
            """
        )
        conn.commit()
        # One directory row per tenant; join returns the current lease where the end date is today or later.
        cursor.execute(
            """
            SELECT
                t.tenantID,
                t.name,
                t.NINumber,
                t.phoneNumber,
                t.email,
                t.occupation,
                COALESCE(
                    CASE
                        WHEN la.leaseID IS NULL THEN NULL
                        WHEN COALESCE(la.lease_state, 'ACTIVE') = 'LEAVING' THEN
                            (a.location || ' - ' || COALESCE(a.type, '') || ' — Leaving')
                        ELSE (a.location || ' - ' || COALESCE(a.type, ''))
                    END,
                    'Unassigned'
                ) AS apartment,
                CASE
                    WHEN la.leaseID IS NULL THEN 'NONE'
                    ELSE COALESCE(la.lease_state, 'ACTIVE')
                END AS lease_state
            FROM tenants t
            LEFT JOIN lease_agreements la ON la.tenantID = t.tenantID
                AND date(la.endDate) >= date('now')
                AND COALESCE(la.lease_state, 'ACTIVE') IN ('ACTIVE', 'LEAVING')
            LEFT JOIN apartments a ON a.apartmentID = la.apartmentID
            GROUP BY t.tenantID
            """
        )
        tenants = cursor.fetchall()
        conn.close()

        self.tenant_table.setRowCount(len(tenants))
        for row, t in enumerate(tenants):
            # Columns 0–5 contain textual cells; column 6 hosts a composite action widget.
            self.tenant_table.setItem(row, 0, QTableWidgetItem(t["name"]))
            self.tenant_table.setItem(row, 1, QTableWidgetItem(t["NINumber"]))
            self.tenant_table.setItem(row, 2, QTableWidgetItem(t["phoneNumber"] or ""))
            self.tenant_table.setItem(row, 3, QTableWidgetItem(t["email"] or ""))
            self.tenant_table.setItem(row, 4, QTableWidgetItem(t["occupation"] or ""))
            apt_item = QTableWidgetItem(t["apartment"] or "Unassigned")
            # Warning palette when the lease state is LEAVING (annotated in the apartment label).
            if (t["lease_state"] or "") == "LEAVING":
                apt_item.setForeground(QColor(app_theme.C_WARNING))
            self.tenant_table.setItem(row, 5, apt_item)

            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(6, 6, 6, 6)
            action_layout.setSpacing(6)

            # Explicit minimum dimensions mitigate global QPushButton styles shrinking table cell controls.
            btn_geom = (
                "min-height: 32px !important; padding: 6px 10px !important; "
                "font-size: 11px; border-radius: 6px; font-weight: 600; border: none;"
            )

            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet(
                f"background-color: {app_theme.C_BG_MUTED}; color: {app_theme.C_TEXT}; {btn_geom}"
            )
            edit_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            edit_btn.setMinimumHeight(32)
            edit_btn.clicked.connect(lambda _, tid=t["tenantID"]: self.edit_tenant(tid))

            early_btn = QPushButton("Early Exit")
            early_btn.setStyleSheet(
                f"background-color: {app_theme.C_WARNING}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
            )
            early_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            early_btn.setMinimumHeight(32)
            early_btn.clicked.connect(lambda _, tid=t["tenantID"], tname=t["name"]: self.early_exit(tid, tname))
            lease_state = t["lease_state"] or "NONE"
            # Early exit enabled only for ACTIVE leases; disabled for LEAVING or absent leases with explanatory tooltips.
            early_btn.setEnabled(lease_state == "ACTIVE")
            if lease_state == "LEAVING":
                early_btn.setToolTip("Early exit has already been processed for this lease.")
            elif lease_state == "NONE":
                early_btn.setToolTip(
                    "No lease on file. Early exit needs an active lease; "
                    "this app only creates a lease when the tenant is registered with an apartment."
                )
            else:
                early_btn.setToolTip("")

            details_btn = QPushButton("Details")
            details_btn.setStyleSheet(
                f"background-color: {app_theme.C_ACCENT}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
            )
            details_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            details_btn.setMinimumHeight(32)
            details_btn.clicked.connect(lambda _, tid=t["tenantID"]: self.show_tenant_details(tid))

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                f"background-color: {app_theme.C_DANGER}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
            )
            del_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            del_btn.setMinimumHeight(32)
            del_btn.clicked.connect(
                lambda _, tid=t["tenantID"], tname=t["name"]: self.delete_tenant(tid, tname)
            )

            action_layout.addWidget(edit_btn)
            action_layout.addWidget(early_btn)
            action_layout.addWidget(details_btn)
            action_layout.addWidget(del_btn)
            action_widget.setLayout(action_layout)
            action_widget.setMinimumHeight(44)
            # Minimum width hint so the actions column reserves adequate horizontal space.
            action_widget.setMinimumWidth(max(action_widget.sizeHint().width(), 348))
            self.tenant_table.setCellWidget(row, 6, action_widget)
            self.tenant_table.resizeRowToContents(row)
            if self.tenant_table.rowHeight(row) < 52:
                self.tenant_table.setRowHeight(row, 52)

        self.tenant_table.resizeColumnToContents(6)

    def show_tenant_details(self, tenant_id: str):
        # Modal dialog presenting read-only tenant, invoice, maintenance, and current lease summaries.
        conn = get_connection()
        cursor = conn.cursor()

        # Primary tenant attributes retrieved from the tenants table.
        cursor.execute(
            "SELECT tenantID, name, NINumber, phoneNumber, email, occupation, apartmentRequirements FROM tenants WHERE tenantID = ?",
            (tenant_id,),
        )
        t = cursor.fetchone()

        if not t:
            conn.close()
            QMessageBox.warning(self, "Not Found", "Tenant not found.")
            return

        # Invoice history across all leases for the tenant, ordered by descending due date.
        cursor.execute(
            """
            SELECT
                i.invoiceID,
                i.amount,
                i.dueDate,
                i.status,
                a.location || ' - ' || COALESCE(a.type,'') AS apartment
            FROM invoices i
            JOIN lease_agreements la ON la.leaseID = i.leaseID
            JOIN apartments a ON a.apartmentID = la.apartmentID
            WHERE la.tenantID = ?
            ORDER BY date(i.dueDate) DESC
            """,
            (tenant_id,),
        )
        invoices = cursor.fetchall()

        # Maintenance requests for apartments linked historically to the tenant's leases.
        cursor.execute(
            """
            SELECT
                mr.requestID,
                a.location || ' - ' || COALESCE(a.type,'') AS apartment,
                mr.description,
                mr.priority,
                mr.status,
                mr.dateReported,
                mr.resolutionDate,
                mr.associatedCost
            FROM maintenance_requests mr
            JOIN apartments a ON a.apartmentID = mr.apartmentID
            WHERE mr.apartmentID IN (
                SELECT apartmentID FROM lease_agreements WHERE tenantID = ?
            )
            ORDER BY date(mr.dateReported) DESC
            """,
            (tenant_id,),
        )
        maintenance = cursor.fetchall()

        # Current lease record, when present, drives the coloured status summary beneath the tenant name.
        cursor.execute(
            """
            SELECT
                COALESCE(la.lease_state, 'ACTIVE') AS lease_state,
                la.endDate,
                a.location || ' - ' || COALESCE(a.type, '') AS apartment
            FROM lease_agreements la
            LEFT JOIN apartments a ON a.apartmentID = la.apartmentID
            WHERE la.tenantID = ?
              AND date(la.endDate) >= date('now')
              AND COALESCE(la.lease_state, 'ACTIVE') IN ('ACTIVE', 'LEAVING')
            ORDER BY date(la.endDate) DESC
            LIMIT 1
            """,
            (tenant_id,),
        )
        cur_lease = cursor.fetchone()

        conn.close()

        # Programmatic dialog layout (no external Qt Designer resource).
        dialog = QDialog(self)
        dialog.setWindowTitle("Tenant Details")
        dialog.setMinimumWidth(900)

        outer = QVBoxLayout()
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header = QLabel(f"{t['name']} ({t['NINumber']})")
        header.setStyleSheet(
            f"color: {app_theme.C_ACCENT_HOVER}; font-size: 16px; font-weight: 600; background: transparent;"
        )
        outer.addWidget(header)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"Phone: {t['phoneNumber'] or ''}"))
        info_row.addWidget(QLabel(f"Email: {t['email'] or ''}"))
        info_row.addWidget(QLabel(f"Occupation: {t['occupation'] or ''}"))
        outer.addLayout(info_row)

        if cur_lease:
            ls = (cur_lease["lease_state"] or "ACTIVE").upper()
            status_word = "Leaving" if ls == "LEAVING" else "Active"
            lease_lbl = QLabel(
                f"Lease: {cur_lease['apartment'] or '—'} — ends {cur_lease['endDate'] or '—'} ({status_word})"
            )
            lease_lbl.setStyleSheet(
                app_theme.SUBTITLE + "background: transparent;"
                if ls != "LEAVING"
                else f"color: {app_theme.C_WARNING}; font-size: 12px; background: transparent;"
            )
            outer.addWidget(lease_lbl)

        outer.addWidget(QLabel("Payment History"))
        # Nested invoice table within the details dialog.
        pay_table = QTableWidget()
        pay_table.setColumnCount(5)
        pay_table.setHorizontalHeaderLabels(["Invoice ID", "Apartment", "Amount (£)", "Due Date", "Status"])
        pay_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        pay_table.setEditTriggers(QTableWidget.NoEditTriggers)
        pay_table.setSelectionBehavior(QTableWidget.SelectRows)
        pay_table.verticalHeader().setVisible(False)
        pay_table.setRowCount(len(invoices))
        for r_idx, inv in enumerate(invoices):
            pay_table.setItem(r_idx, 0, QTableWidgetItem(str(inv["invoiceID"])))
            pay_table.setItem(r_idx, 1, QTableWidgetItem(inv["apartment"] or ""))
            amt = inv["amount"]
            pay_table.setItem(r_idx, 2, QTableWidgetItem(f"{float(amt):.2f}" if amt is not None else "0.00"))
            pay_table.setItem(r_idx, 3, QTableWidgetItem(inv["dueDate"] or ""))
            pay_table.setItem(r_idx, 4, QTableWidgetItem(inv["status"] or ""))
        outer.addWidget(pay_table)

        outer.addWidget(QLabel("Maintenance / Complaints"))
        maint_table = QTableWidget()
        maint_table.setColumnCount(8)
        maint_table.setHorizontalHeaderLabels(
            ["Request ID", "Apartment", "Description", "Priority", "Status", "Date Reported", "Resolution Date", "Cost (£)"]
        )
        maint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        maint_table.setEditTriggers(QTableWidget.NoEditTriggers)
        maint_table.setSelectionBehavior(QTableWidget.SelectRows)
        maint_table.verticalHeader().setVisible(False)
        maint_table.setRowCount(len(maintenance))
        for r_idx, mr in enumerate(maintenance):
            maint_table.setItem(r_idx, 0, QTableWidgetItem(str(mr["requestID"])))
            maint_table.setItem(r_idx, 1, QTableWidgetItem(mr["apartment"] or ""))
            maint_table.setItem(r_idx, 2, QTableWidgetItem((mr["description"] or "")[:80]))
            maint_table.setItem(r_idx, 3, QTableWidgetItem(mr["priority"] or ""))
            maint_table.setItem(r_idx, 4, QTableWidgetItem(mr["status"] or ""))
            maint_table.setItem(r_idx, 5, QTableWidgetItem(mr["dateReported"] or ""))
            maint_table.setItem(r_idx, 6, QTableWidgetItem(mr["resolutionDate"] or ""))
            cost = mr["associatedCost"]
            maint_table.setItem(r_idx, 7, QTableWidgetItem(f"{float(cost):.2f}" if cost is not None else "0.00"))
        outer.addWidget(maint_table)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(dialog.reject)
        close_buttons.accepted.connect(dialog.accept)
        outer.addWidget(close_buttons)

        dialog.setLayout(outer)
        dialog.exec_()

    def register_tenant(self):
        # Copy registration form inputs into local variables for validation and persistence.
        name = self.t_name.text().strip()
        ni = self.t_ni.text().strip().upper()
        phone = normalize_uk_mobile(self.t_phone.text())
        email = self.t_email.text().strip()
        occupation = self.t_occupation.text().strip()
        references = self.t_references.text().strip()
        apt_req = self.t_apt_req.text().strip()
        apt_id = self.t_apt_combo.currentData()
        start = self.t_start_date.date().toString("yyyy-MM-dd")
        end = self.t_end_date.date().toString("yyyy-MM-dd")
        deposit = self.t_deposit.value()

        # --- Validation: terminate on first failed rule with an appropriate message box ---
        if not name or not ni:
            QMessageBox.warning(self, "Validation Error", "Full Name and NI Number are required.")
            return

        if not is_valid_uk_mobile(phone):
            QMessageBox.warning(
                self,
                "Invalid phone number",
                f"Please enter a UK mobile number as 11 digits starting with 07 (e.g. 07545798234).\n"
                f"{uk_mobile_format_hint()} Only digits are allowed.",
            )
            return

        if not email:
            QMessageBox.warning(self, "Validation Error", "Email is required (must include '@').")
            return

        if not is_valid_email(email):
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address (must include '@').")
            return

        # National Insurance format validated independently from email and telephone rules.
        import re
        if not re.match(r'^[A-Z]{2}\d{6}[A-Z]$', ni):
            QMessageBox.warning(self, "Validation Error",
                                "NI Number format is invalid.\nExpected format: AB123456C")
            return

        sd = self.t_start_date.date()
        ed = self.t_end_date.date()
        if sd.daysTo(ed) < 1:
            QMessageBox.warning(
                self,
                "Invalid lease dates",
                "The lease end date must be at least one calendar day after the lease start date.",
            )
            return

        # Backend & Database — Finn Lennaghan (24024274): tenant + optional lease + invoice persistence (with checks).
        # --- Persistence: always insert tenant; create lease and opening invoice only when an apartment is selected ---
        conn = get_connection()
        cursor = conn.cursor()

        # Enforce unique National Insurance numbers at the application layer prior to insert.
        cursor.execute("SELECT 1 FROM tenants WHERE NINumber = ?", (ni,))
        if cursor.fetchone():
            conn.close()
            QMessageBox.warning(self, "Duplicate NI", f"A tenant with NI Number '{ni}' already exists.")
            return

        # Backend & Database — Finn Lennaghan (24024274): INSERT/UPDATE transaction for new tenant (+ lease path).
        try:
            tenant_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tenants (tenantID, NINumber, name, phoneNumber, email,
                                     occupation, references_, apartmentRequirements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tenant_id, ni, name, phone, email, occupation, references, apt_req))

            # Insert lease_agreements when an apartment identifier is supplied.
            if apt_id:
                lease_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO lease_agreements
                        (leaseID, tenantID, apartmentID, startDate, endDate, depositAmount, lease_state)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                """, (lease_id, tenant_id, apt_id, start, end, deposit))

                cursor.execute(
                    "UPDATE apartments SET occupancyStatus = 1 WHERE apartmentID = ?", (apt_id,)
                )

                # Seed an initial rent invoice linked to the new lease.
                invoice_id = str(uuid.uuid4())
                cursor.execute("""
                    SELECT monthlyRent FROM apartments WHERE apartmentID = ?
                """, (apt_id,))
                apt_row = cursor.fetchone()
                if apt_row:
                    cursor.execute("""
                        INSERT INTO invoices (invoiceID, leaseID, amount, dueDate, status)
                        VALUES (?, ?, ?, ?, 'UNPAID')
                    """, (invoice_id, lease_id, apt_row['monthlyRent'], end))

            conn.commit()
            extra = (
                "\nApartment assigned and first invoice created."
                if apt_id
                else "\nThe tenant is listed as Unassigned."
            )
            QMessageBox.information(self, "Success", f"Tenant '{name}' registered successfully!{extra}")
            self._clear_tenant_form()
            self._load_available_apartments()
            self.load_tenants()
            self._load_all_apartments_for_maintenance()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Registration failed:\n{e}")
        finally:
            conn.close()

    def _clear_tenant_form(self):
        # Reset the form after successful registration to prepare for the next entry.
        for w in [self.t_name, self.t_ni, self.t_phone, self.t_email,
                  self.t_occupation, self.t_references, self.t_apt_req]:
            w.clear()
        self.t_start_date.setDate(QDate.currentDate())
        self.t_end_date.setDate(QDate.currentDate().addYears(1))
        self.t_deposit.setValue(1200)
        self.t_apt_combo.setCurrentIndex(0)
        self._tenant_lease_start_changed()
        self._tenant_lease_end_changed()

    def _tenant_lease_start_changed(self, _new_date=None):
        # When the start date advances, enforce a minimum end date one day after the start.
        start = self.t_start_date.date()
        min_end = start.addDays(1)
        self.t_end_date.blockSignals(True)
        self.t_end_date.setMinimumDate(min_end)
        if self.t_end_date.date() <= start:
            self.t_end_date.setDate(start.addYears(1))
        self.t_end_date.blockSignals(False)

    def _tenant_lease_end_changed(self, _new_date=None):
        # When the end date moves earlier, constrain the start date to remain strictly before the end.
        end = self.t_end_date.date()
        max_start = end.addDays(-1)
        self.t_start_date.blockSignals(True)
        self.t_start_date.setMaximumDate(max_start)
        if self.t_start_date.date() >= end:
            self.t_start_date.setDate(max_start)
        self.t_start_date.blockSignals(False)

    def edit_tenant(self, tenant_id):
        # Limited-field edit dialog; National Insurance remains immutable as the natural key.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tenants WHERE tenantID = ?", (tenant_id,))
        t = cursor.fetchone()
        conn.close()
        if not t:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Tenant")
        dialog.setMinimumWidth(400)

        form = QFormLayout()
        fields = {
            'name':        QLineEdit(t['name'] or ''),
            'phoneNumber': QLineEdit(t['phoneNumber'] or ''),
            'email':       QLineEdit(t['email'] or ''),
            'occupation':  QLineEdit(t['occupation'] or ''),
        }
        attach_uk_mobile_input(fields['phoneNumber'])
        fields['phoneNumber'].setPlaceholderText("07545798234")
        form.addRow("Full Name:",  fields['name'])
        form.addRow("Phone:",      fields['phoneNumber'])
        form.addRow("Email:",      fields['email'])
        form.addRow("Occupation:", fields['occupation'])

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        vbox = QVBoxLayout()
        vbox.addLayout(form)
        vbox.addWidget(buttons)
        dialog.setLayout(vbox)

        if dialog.exec_() == QDialog.Accepted:
            # Open a new connection for the UPDATE after the initial SELECT connection was closed.
            conn = get_connection()
            # Backend & Database — Finn Lennaghan (24024274): persist edited tenant fields after validation.
            try:
                updated_email = fields["email"].text().strip()
                updated_phone = normalize_uk_mobile(fields["phoneNumber"].text())
                if not updated_email or not is_valid_email(updated_email):
                    QMessageBox.warning(
                        self,
                        "Validation Error",
                        "Please enter a valid email address (must include '@').",
                    )
                    conn.close()
                    return

                if not is_valid_uk_mobile(updated_phone):
                    QMessageBox.warning(
                        self,
                        "Invalid phone number",
                        f"Please enter a UK mobile number as 11 digits starting with 07 (e.g. 07545798234).\n"
                        f"{uk_mobile_format_hint()}",
                    )
                    conn.close()
                    return

                conn.execute("""
                    UPDATE tenants
                    SET name=?, phoneNumber=?, email=?, occupation=?
                    WHERE tenantID=?
                """, (
                    fields['name'].text().strip(),
                    updated_phone,
                    updated_email,
                    fields['occupation'].text().strip(),
                    tenant_id
                ))
                conn.commit()
                self.load_tenants()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
            finally:
                conn.close()

    def early_exit(self, tenant_id, tenant_name):
        # Backend & Database — Finn Lennaghan (24024274): load active lease row used for fee + later updates.
        # Select the single ACTIVE lease eligible for early termination.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT la.leaseID, la.endDate, a.monthlyRent, a.apartmentID
            FROM lease_agreements la
            JOIN apartments a ON a.apartmentID = la.apartmentID
            WHERE la.tenantID = ?
              AND date(la.endDate) >= date('now')
              AND COALESCE(la.lease_state, 'ACTIVE') = 'ACTIVE'
            ORDER BY la.endDate DESC LIMIT 1
        """, (tenant_id,))
        lease = cursor.fetchone()
        conn.close()

        if not lease:
            # Absence of a qualifying lease surfaces a warning rather than raising an exception.
            QMessageBox.information(
                self,
                "Early exit not available",
                f"{tenant_name} has no active lease eligible for early exit, or early exit was already processed.",
            )
            return

        # Backend & Database — Finn Lennaghan (24024274): early-exit penalty calculated as five percent of monthly rent per specification.
        penalty = round(lease['monthlyRent'] * 0.05, 2)

        today_date = date.today()
        # Assignment rule: tenant notice date must be at least one calendar month prior to the selected exit date.
        notice_min_date = today_date - timedelta(days=30)

        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Early Exit (Notice Required)")
        dialog.setMinimumWidth(500)

        outer = QVBoxLayout()
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        summary = QLabel(
            f"Tenant: {tenant_name}\n"
            f"Original end date: {lease['endDate']}\n\n"
            f"Penalty (5% of monthly rent): £{penalty:.2f}\n"
        )
        summary.setStyleSheet(f"color: {app_theme.C_TEXT}; background: transparent;")
        outer.addWidget(summary)

        notice_lbl = QLabel("Notice date (when tenant requested early exit):")
        outer.addWidget(notice_lbl)

        notice_edit = QDateEdit()
        notice_edit.setCalendarPopup(True)
        notice_edit.setDate(QDate(notice_min_date.year, notice_min_date.month, notice_min_date.day))
        outer.addWidget(notice_edit)

        helper_lbl = QLabel("Validation: notice date must be at least 1 month (30 days) before today.")
        helper_lbl.setStyleSheet(app_theme.SUBTITLE + "background: transparent;")
        outer.addWidget(helper_lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        outer.addWidget(buttons)

        dialog.setLayout(outer)
        if dialog.exec_() != QDialog.Accepted:
            return

        # Convert QDate values to datetime.date instances for comparison logic.
        notice_date_py = notice_edit.date().toPyDate()
        if notice_date_py > notice_min_date:
            QMessageBox.warning(
                self,
                "Notice Policy",
                "Early exit requires at least 1 month notice (30 days).",
            )
            return
        if notice_date_py > today_date:
            QMessageBox.warning(
                self,
                "Notice Policy",
                "Notice date cannot be in the future.",
            )
            return

        today = today_date.isoformat()
        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): apply early exit, vacancy, maintenance cleanup, penalty invoice.
        try:
            # Set lease end to the current date and mark LEAVING to coordinate downstream maintenance rules.
            conn.execute("""
                UPDATE lease_agreements
                SET endDate = ?, penaltyApplied = ?, lease_state = 'LEAVING'
                WHERE leaseID = ?
            """, (today, penalty, lease['leaseID']))

            # Update apartment occupancy so administrative and managerial dashboards reflect vacancy.
            conn.execute("""
                UPDATE apartments SET occupancyStatus = 0 WHERE apartmentID = ?
            """, (lease['apartmentID'],))

            # Remove maintenance requests for the apartment while a tenant is in LEAVING status.
            conn.execute(
                "DELETE FROM maintenance_requests WHERE apartmentID = ?",
                (lease["apartmentID"],),
            )

            # Insert penalty invoice linked to the existing lease for finance reporting continuity.
            inv_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO invoices (invoiceID, leaseID, amount, dueDate, status)
                VALUES (?, ?, ?, ?, 'UNPAID')
            """, (inv_id, lease['leaseID'], penalty, today))

            conn.commit()
            QMessageBox.information(
                self,
                "Early Exit Processed",
                f"Lease terminated. Penalty invoice of £{penalty:.2f} has been raised.\n"
                "All maintenance requests for this apartment have been removed.",
            )
            self._load_available_apartments()
            self.load_tenants()
            self._load_all_apartments_for_maintenance()
            self.load_maintenance_requests()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()

    def delete_tenant(self, tenant_id: str, tenant_name: str):
        # Permanent deletion path removing the tenant graph and restoring apartment occupancy where applicable.
        reply = QMessageBox.question(
            self,
            "Delete tenant",
            f'Permanently remove tenant "{tenant_name}" and all of their leases and '
            "invoices from the system? This cannot be undone.\n\n"
            "All maintenance requests for apartments linked to this tenant will also be removed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): cascade delete tenant → leases → invoices → maintenance; fix occupancy.
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT leaseID, apartmentID FROM lease_agreements WHERE tenantID = ?",
                (tenant_id,),
            )
            leases = cur.fetchall()

            # Delete dependent invoice rows before removing parent lease records (foreign key ordering).
            lease_ids = [row["leaseID"] for row in leases]
            if lease_ids:
                placeholders = ",".join("?" * len(lease_ids))
                cur.execute(
                    f"DELETE FROM invoices WHERE leaseID IN ({placeholders})",
                    lease_ids,
                )

            # Remove maintenance requests for apartments referenced by the tenant's leases.
            apt_ids = {row["apartmentID"] for row in leases if row["apartmentID"]}
            if apt_ids:
                apt_ph = ",".join("?" * len(apt_ids))
                cur.execute(
                    f"DELETE FROM maintenance_requests WHERE apartmentID IN ({apt_ph})",
                    tuple(apt_ids),
                )
            for apt_id in apt_ids:
                # When no other active lease references the apartment, reset occupancy to vacant.
                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM lease_agreements
                    WHERE apartmentID = ? AND tenantID != ? AND date(endDate) >= date('now')
                    """,
                    (apt_id, tenant_id),
                )
                if int(cur.fetchone()["c"] or 0) == 0:
                    cur.execute(
                        "UPDATE apartments SET occupancyStatus = 0 WHERE apartmentID = ?",
                        (apt_id,),
                    )

            cur.execute("DELETE FROM lease_agreements WHERE tenantID = ?", (tenant_id,))
            cur.execute("DELETE FROM tenants WHERE tenantID = ?", (tenant_id,))
            conn.commit()
            QMessageBox.information(
                self,
                "Tenant removed",
                f'"{tenant_name}" has been removed from the register.',
            )
            self._load_available_apartments()
            self.load_tenants()
            self._load_all_apartments_for_maintenance()
            self.load_maintenance_requests()
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Could not delete tenant", str(e))
        finally:
            conn.close()

    # --- Page 2: maintenance intake form, request register, and status-specific removal actions ---

    def build_maintenance_panel(self):
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        title = QLabel("Maintenance Requests")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        # Upper card: apartment selector, priority, description, and submission control.
        form_frame = QFrame()
        form_frame.setObjectName("FormCard")
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(10)

        form_lbl = QLabel("Log New Maintenance Request")
        form_lbl.setStyleSheet(app_theme.SECTION_TITLE + "font-size: 14px; background: transparent;")
        form_layout.addWidget(form_lbl)

        row1 = QHBoxLayout()
        apt_lbl = QLabel("Apartment:")
        apt_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.m_apt_combo = QComboBox()
        self._load_all_apartments_for_maintenance()

        priority_lbl = QLabel("Priority:")
        priority_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.m_priority = QComboBox()
        self.m_priority.addItems(["LOW", "MEDIUM", "HIGH", "URGENT"])
        self.m_priority.setCurrentText("MEDIUM")

        row1.addWidget(apt_lbl)
        row1.addWidget(self.m_apt_combo)
        row1.addWidget(priority_lbl)
        row1.addWidget(self.m_priority)
        form_layout.addLayout(row1)

        desc_lbl = QLabel("Description:")
        desc_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.m_desc = QTextEdit()
        self.m_desc.setPlaceholderText("Describe the maintenance issue in detail...")
        self.m_desc.setFixedHeight(70)
        form_layout.addWidget(desc_lbl)
        form_layout.addWidget(self.m_desc)

        btn_row = QHBoxLayout()
        submit_btn = QPushButton("Submit Request")
        submit_btn.setFixedWidth(180)
        submit_btn.clicked.connect(self.submit_maintenance_request)
        btn_row.addStretch()
        btn_row.addWidget(submit_btn)
        form_layout.addLayout(btn_row)

        form_frame.setLayout(form_layout)

        # Status filter triggers load_maintenance_requests with an additional WHERE predicate when not ALL.
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("Filter by status:")
        filter_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")
        self.m_status_filter = QComboBox()
        self.m_status_filter.addItems(["ALL", "PENDING", "IN_PROGRESS", "RESOLVED"])
        self.m_status_filter.currentTextChanged.connect(self.load_maintenance_requests)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self.m_status_filter)
        filter_row.addStretch()

        self.maint_table = QTableWidget()
        self.maint_table.setColumnCount(8)
        self.maint_table.setHorizontalHeaderLabels([
            "Apartment",
            "Description",
            "Priority",
            "Status",
            "Date Reported",
            "Scheduled visit",
            "Tenant liaison",
            "Action",
        ])
        m_hdr = self.maint_table.horizontalHeader()
        for col in range(7):
            m_hdr.setSectionResizeMode(col, QHeaderView.Stretch)
        m_hdr.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.maint_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.maint_table.setSelectionBehavior(QTableWidget.SelectRows)
        m_vh = self.maint_table.verticalHeader()
        m_vh.setVisible(False)
        m_vh.setDefaultSectionSize(52)
        m_vh.setMinimumSectionSize(48)
        self.maint_table.setMinimumHeight(280)

        self.m_maint_empty_hint = QLabel(
            "No maintenance requests match this filter. Choose ALL or submit a new job above."
        )
        self.m_maint_empty_hint.setWordWrap(True)
        self.m_maint_empty_hint.setStyleSheet(app_theme.HINT + "background: transparent;")
        self.m_maint_empty_hint.setVisible(False)

        # Vertical stack: page heading, intake card, filter row, data table, and empty-state hint.
        outer.addWidget(title)
        outer.addWidget(form_frame)
        outer.addLayout(filter_row)
        outer.addWidget(self.maint_table)
        outer.addWidget(self.m_maint_empty_hint)
        container.setLayout(outer)

        self.load_maintenance_requests()
        return container

    def _load_all_apartments_for_maintenance(self):
        # Occupied flats only (vacant units cannot log tenant repairs). Still hide LEAVING while lease runs.
        self.m_apt_combo.clear()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT a.apartmentID, a.location, a.type
            FROM apartments a
            WHERE a.occupancyStatus = 1
              AND NOT EXISTS (
                SELECT 1 FROM lease_agreements la
                WHERE la.apartmentID = a.apartmentID
                  AND date(la.endDate) >= date('now')
                  AND COALESCE(la.lease_state, 'ACTIVE') = 'LEAVING'
            )
            ORDER BY a.location, COALESCE(a.type, '')
            """
        )
        for apt in cursor.fetchall():
            label = f"{apt['location']} | {apt['type'] or 'N/A'}"
            self.m_apt_combo.addItem(label, apt['apartmentID'])
        conn.close()

    def load_maintenance_requests(self):
        # getattr protects against invocation before the maintenance widgets are constructed.
        status_filter = getattr(self, 'm_status_filter', None)
        filter_val = status_filter.currentText() if status_filter else "ALL"

        conn = get_connection()
        cursor = conn.cursor()

        # Shared ORDER BY; optional WHERE clause depends on the selected status filter.
        if filter_val == "ALL":
            cursor.execute("""
                SELECT mr.requestID, a.location || ' - ' || COALESCE(a.type,'') as apt,
                       mr.description, mr.priority, mr.status, mr.dateReported,
                       mr.scheduledVisitDate, mr.tenantCommunicationNote
                FROM maintenance_requests mr
                JOIN apartments a ON a.apartmentID = mr.apartmentID
                ORDER BY
                    CASE mr.priority
                        WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3 ELSE 4
                    END,
                    mr.dateReported DESC
            """)
        else:
            cursor.execute("""
                SELECT mr.requestID, a.location || ' - ' || COALESCE(a.type,'') as apt,
                       mr.description, mr.priority, mr.status, mr.dateReported,
                       mr.scheduledVisitDate, mr.tenantCommunicationNote
                FROM maintenance_requests mr
                JOIN apartments a ON a.apartmentID = mr.apartmentID
                WHERE mr.status = ?
                ORDER BY
                    CASE mr.priority
                        WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3 ELSE 4
                    END,
                    mr.dateReported DESC
            """, (filter_val,))

        requests = cursor.fetchall()
        conn.close()

        if hasattr(self, "m_maint_empty_hint"):
            self.m_maint_empty_hint.setVisible(len(requests) == 0)

        self.maint_table.setRowCount(len(requests))
        # Map theme hex constants to QColor instances for table item foreground styling.
        priority_colors = {
            "URGENT": app_theme.C_DANGER,
            "HIGH": app_theme.C_WARNING,
            "MEDIUM": app_theme.C_TEXT_MUTED,
            "LOW": app_theme.C_SUCCESS,
        }
        status_colors = {
            "PENDING": app_theme.C_WARNING,
            "IN_PROGRESS": app_theme.C_ACCENT_HOVER,
            "RESOLVED": app_theme.C_SUCCESS,
        }

        for row, req in enumerate(requests):
            self.maint_table.setItem(row, 0, QTableWidgetItem(req["apt"]))

            # Truncate long descriptions to preserve consistent row height in the grid.
            desc = req["description"] or ""
            short_desc = desc[:60] + "..." if len(desc) > 60 else desc
            self.maint_table.setItem(row, 1, QTableWidgetItem(short_desc))

            priority_item = QTableWidgetItem(req["priority"])
            priority_item.setForeground(
                QColor(priority_colors.get(req["priority"], app_theme.C_TEXT))
            )
            self.maint_table.setItem(row, 2, priority_item)

            status_item = QTableWidgetItem(req["status"])
            status_item.setForeground(
                QColor(status_colors.get(req["status"], app_theme.C_TEXT))
            )
            self.maint_table.setItem(row, 3, status_item)
            self.maint_table.setItem(row, 4, QTableWidgetItem(req["dateReported"] or ""))
            self.maint_table.setItem(row, 5, QTableWidgetItem(req["scheduledVisitDate"] or ""))
            lia = req["tenantCommunicationNote"] or ""
            lia_short = lia[:40] + "..." if len(lia) > 40 else lia
            lia_item = QTableWidgetItem(lia_short)
            lia_item.setToolTip(lia)
            self.maint_table.setItem(row, 6, lia_item)

            st = req["status"] or ""
            # Button label reflects status: Cancel for pending requests, Remove for other states; both execute DELETE.
            btn_label = "Cancel" if st == "PENDING" else "Remove"
            act_wrap = QWidget()
            act_layout = QHBoxLayout(act_wrap)
            act_layout.setContentsMargins(6, 6, 6, 6)
            act_layout.setSpacing(0)
            btn_geom = (
                "min-height: 32px !important; padding: 6px 12px !important; "
                "font-size: 11px; border-radius: 6px; font-weight: 600; border: none;"
            )
            del_btn = QPushButton(btn_label)
            del_btn.setStyleSheet(
                f"background-color: {app_theme.C_DANGER}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
            )
            del_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            del_btn.setMinimumHeight(32)
            del_btn.clicked.connect(
                lambda _, rid=req["requestID"], s=st: self.cancel_request(rid, s)
            )
            act_layout.addWidget(del_btn)
            act_wrap.setMinimumWidth(max(act_wrap.sizeHint().width(), 100))
            act_wrap.setMinimumHeight(44)
            self.maint_table.setCellWidget(row, 7, act_wrap)
            self.maint_table.resizeRowToContents(row)
            if self.maint_table.rowHeight(row) < 52:
                self.maint_table.setRowHeight(row, 52)

        self.maint_table.resizeColumnToContents(7)

    def submit_maintenance_request(self):
        # Resolve apartmentID from combo itemData rather than parsing the visible label text.
        apt_id = self.m_apt_combo.currentData()
        description = self.m_desc.toPlainText().strip()
        priority = self.m_priority.currentText()

        if not apt_id:
            QMessageBox.warning(self, "Validation Error", "Please select an apartment.")
            return
        if not description:
            QMessageBox.warning(self, "Validation Error", "Please provide a description.")
            return
        if len(description) < 10:
            QMessageBox.warning(self, "Validation Error",
                                "Description is too short (minimum 10 characters).")
            return

        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): LEAVING guard + INSERT new maintenance_requests row.
        try:
            cur = conn.cursor()
            # Block new tickets while a tenant is in LEAVING state on this flat.
            cur.execute(
                """
                SELECT 1 FROM lease_agreements
                WHERE apartmentID = ?
                  AND date(endDate) >= date('now')
                  AND COALESCE(lease_state, 'ACTIVE') = 'LEAVING'
                LIMIT 1
                """,
                (apt_id,),
            )
            if cur.fetchone():
                QMessageBox.warning(
                    self,
                    "Cannot add maintenance",
                    "This apartment has a tenant on early exit (Leaving). "
                    "New maintenance requests cannot be logged for this unit until the lease has ended.",
                )
                return
            cur.execute(
                "SELECT occupancyStatus FROM apartments WHERE apartmentID = ?",
                (apt_id,),
            )
            occ_row = cur.fetchone()
            if not occ_row or not occ_row["occupancyStatus"]:
                QMessageBox.warning(
                    self,
                    "Cannot add maintenance",
                    "Maintenance requests can only be logged for occupied apartments.",
                )
                return
            # New requests default to PENDING until updated by maintenance staff.
            cur.execute(
                """
                INSERT INTO maintenance_requests
                    (requestID, apartmentID, description, priority, status, dateReported)
                VALUES (?, ?, ?, ?, 'PENDING', date('now'))
                """,
                (str(uuid.uuid4()), apt_id, description, priority),
            )
            conn.commit()
            QMessageBox.information(self, "Success", "Maintenance request submitted successfully.")
            self.m_desc.clear()
            self.m_priority.setCurrentText("MEDIUM")
            self.load_maintenance_requests()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()

    def cancel_request(self, request_id, status):
        # Confirmation copy varies with request status to describe operational impact.
        if status == "RESOLVED":
            reply = QMessageBox.question(
                self,
                "Remove completed request",
                "Remove this resolved maintenance record from the system? This cannot be undone.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        elif status == "IN_PROGRESS":
            reply = QMessageBox.question(
                self,
                "Remove in-progress request",
                "This request is in progress. Deleting it cannot be undone and may confuse "
                "staff if they are already working on it. Remove anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
        else:
            reply = QMessageBox.question(
                self,
                "Cancel request",
                "Cancel this pending maintenance request? It will be removed from the list.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

        if reply != QMessageBox.Yes:
            return

        # Backend & Database — Finn Lennaghan (24024274): remove one maintenance_requests row after confirmation.
        # Single-row deletion; other roles observe the removal after their next data refresh.
        conn = get_connection()
        try:
            conn.execute(
                "DELETE FROM maintenance_requests WHERE requestID = ?", (request_id,)
            )
            conn.commit()
            QMessageBox.information(self, "Removed", "Maintenance request removed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
            self.load_maintenance_requests()
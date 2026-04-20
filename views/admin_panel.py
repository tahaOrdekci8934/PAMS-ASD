        # Backend & Database — Finn Lennaghan (24024274): insert new staff user (hashed password, unique email).
class AdminPanel(QWidget):
    def __init__(self, user):
        super().__init__()        

    def add_user(self): 
        if not self._require_admin():
            return
        
        name = self.u_name.text().strip()
        email = self.u_email.text().strip().lower()
        password = self.u_pass.text().strip()
        role = self.u_role.currentText()

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
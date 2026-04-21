        # Backend & Database — Finn Lennaghan (24024274): read-only SQL aggregates for occupancy by city.
        # occupancyStatus 1 = occupied, 0 = available; occupancy rate percentage computed in Python.
class ManagerPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

    def load_occupancy(self):        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                location,
                COUNT(*) AS total,
                SUM(CASE WHEN occupancyStatus = 1 THEN 1 ELSE 0 END) AS occupied,
                SUM(CASE WHEN occupancyStatus = 0 THEN 1 ELSE 0 END) AS available
            FROM apartments
            GROUP BY location
            ORDER BY location
            """
        )
        rows = cursor.fetchall()
        conn.close()

        self.occupancy_table.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            # Avoid division by zero when no apartment rows exist for a location.
            location = r["location"] or ""
            total = int(r["total"] or 0)
            occupied = int(r["occupied"] or 0)
            available = int(r["available"] or 0)
            occupancy_rate = (occupied / total * 100.0) if total > 0 else 0.0

            self.occupancy_table.setItem(idx, 0, QTableWidgetItem(location))
            self.occupancy_table.setItem(idx, 1, QTableWidgetItem(str(total)))
            self.occupancy_table.setItem(idx, 2, QTableWidgetItem(str(occupied)))
            self.occupancy_table.setItem(idx, 3, QTableWidgetItem(str(available)))
            self.occupancy_table.setItem(idx, 4, QTableWidgetItem(f"{occupancy_rate:.1f}%"))

    def build_reports_panel(self):
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        card = QFrame()
        card.setObjectName("FormCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("Performance Reports")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        fin_hdr = QLabel("Financial breakdown by location")
        fin_hdr.setStyleSheet(app_theme.SECTION_TITLE + "background: transparent;")

        self.fin_table = QTableWidget()
        self.fin_table.setColumnCount(4)
        self.fin_table.setHorizontalHeaderLabels(["Location", "Collected (£)", "Pending (£)", "Late Count"])
        self.fin_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fin_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fin_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fin_table.verticalHeader().setVisible(False)
        self.fin_table.setMinimumHeight(230)

        maint_hdr = QLabel("Maintenance costs by location")
        maint_hdr.setStyleSheet(app_theme.SECTION_TITLE + "background: transparent;")

        self.maint_table = QTableWidget()
        self.maint_table.setColumnCount(4)
        self.maint_table.setHorizontalHeaderLabels(["Location", "Resolved Count", "Total Cost (£)", "Avg Cost (£)"])
        self.maint_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.maint_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.maint_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.maint_table.verticalHeader().setVisible(False)
        self.maint_table.setMinimumHeight(230)

        card_layout.addWidget(title)
        card_layout.addWidget(fin_hdr)
        card_layout.addWidget(self.fin_table)
        card_layout.addWidget(maint_hdr)
        card_layout.addWidget(self.maint_table)
        outer.addWidget(card)
        container.setLayout(outer)
        return container

    def load_reports(self):
        # Backend & Database — Finn Lennaghan (24024274): read-only reporting queries (finance + maintenance).
        # First query matches the finance per-location invoice breakdown; second covers resolved maintenance only.
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                a.location AS location,
                COALESCE(SUM(CASE WHEN i.status = 'PAID' THEN i.amount ELSE 0 END), 0) AS collected,
                COALESCE(SUM(CASE WHEN i.status = 'UNPAID' THEN i.amount ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN i.status = 'UNPAID' AND date(i.dueDate) < date('now') THEN 1 ELSE 0 END), 0) AS lateCount
            FROM invoices i
            JOIN lease_agreements la ON la.leaseID = i.leaseID
            JOIN apartments a ON a.apartmentID = la.apartmentID
            GROUP BY a.location
            ORDER BY a.location
            """
        )
        fin_rows = cursor.fetchall()
        self.fin_table.setRowCount(len(fin_rows))
        for idx, r in enumerate(fin_rows):
            # Column layout aligned with the finance per-location table for cross-screen comparison.
            self.fin_table.setItem(idx, 0, QTableWidgetItem(r["location"] or ""))
            self.fin_table.setItem(idx, 1, QTableWidgetItem(f"{float(r['collected'] or 0):.2f}"))
            self.fin_table.setItem(idx, 2, QTableWidgetItem(f"{float(r['pending'] or 0):.2f}"))
            self.fin_table.setItem(idx, 3, QTableWidgetItem(str(int(r["lateCount"] or 0))))

        # Maintenance aggregates include RESOLVED requests only; open jobs are excluded from cost totals.
        cursor.execute(
            """
            SELECT
                a.location AS location,
                COUNT(*) AS resolvedCount,
                COALESCE(SUM(COALESCE(mr.associatedCost, 0)), 0) AS totalCost,
                CASE WHEN COUNT(*) = 0 THEN 0 ELSE
                    COALESCE(SUM(COALESCE(mr.associatedCost, 0)) / COUNT(*), 0)
                END AS avgCost
            FROM maintenance_requests mr
            JOIN apartments a ON a.apartmentID = mr.apartmentID
            WHERE mr.status = 'RESOLVED'
            GROUP BY a.location
            ORDER BY a.location
            """
        )
        maint_rows = cursor.fetchall()
        self.maint_table.setRowCount(len(maint_rows))
        for idx, r in enumerate(maint_rows):
            # Average cost computed in SQL as total divided by resolved count; display as formatted currency.
            self.maint_table.setItem(idx, 0, QTableWidgetItem(r["location"] or ""))
            self.maint_table.setItem(idx, 1, QTableWidgetItem(str(int(r["resolvedCount"] or 0))))
            self.maint_table.setItem(idx, 2, QTableWidgetItem(f"{float(r['totalCost'] or 0):.2f}"))
            self.maint_table.setItem(idx, 3, QTableWidgetItem(f"{float(r['avgCost'] or 0):.2f}"))

        conn.close()

    def build_locations_panel(self):
        # Location selector and read-only apartment table (no edit actions on this screen).
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        card = QFrame()
        card.setObjectName("FormCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("Manage Locations")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        controls = QHBoxLayout()
        controls_lbl = QLabel("Location:")
        controls_lbl.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")

        self.location_filter = QComboBox()
        self.location_filter.currentTextChanged.connect(self.load_location_apartments)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_locations)

        controls.addWidget(controls_lbl)
        controls.addWidget(self.location_filter)
        controls.addWidget(refresh_btn)
        controls.addStretch()

        self.location_apt_table = QTableWidget()
        self.location_apt_table.setColumnCount(5)
        self.location_apt_table.setHorizontalHeaderLabels(
            ["Apartment ID", "Type", "Monthly Rent (£)", "Rooms", "Status"]
        )
        self.location_apt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.location_apt_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.location_apt_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.location_apt_table.verticalHeader().setVisible(False)
        self.location_apt_table.setMinimumHeight(330)

        card_layout.addWidget(title)
        card_layout.addLayout(controls)
        card_layout.addWidget(self.location_apt_table)
        outer.addWidget(card)
        container.setLayout(outer)
        return container

    def load_locations(self):
        # Reload distinct locations from the database so new apartments appear after administrative changes.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM apartments ORDER BY location")
        locations = [r["location"] for r in cursor.fetchall()]
        conn.close()

        self.location_filter.blockSignals(True)
        self.location_filter.clear()

        if not locations:
            self.location_filter.addItem("-- No locations --", None)
            self.location_filter.setEnabled(False)
            self.location_apt_table.setRowCount(0)
            self.location_filter.blockSignals(False)
            return

        self.location_filter.setEnabled(True)
        for loc in locations:
            self.location_filter.addItem(loc, loc)

        # Populate the apartment table for the first location entry after rebuilding the combo box.
        self.location_filter.blockSignals(False)
        current_loc = self.location_filter.itemData(0)
        self.load_location_apartments(current_loc)

    def load_location_apartments(self, location):
        # Ignore empty location values emitted when the combo box is disabled or cleared.
        if not location:
            return

        # Backend & Database — Finn Lennaghan (24024274): list apartments for one location (read-only).
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                apartmentID,
                type,
                monthlyRent,
                numberOfRooms,
                occupancyStatus
            FROM apartments
            WHERE location = ?
            ORDER BY type, monthlyRent
            """,
            (location,),
        )
        rows = cursor.fetchall()
        conn.close()

        self.location_apt_table.setRowCount(len(rows))
        for idx, r in enumerate(rows):
            self.location_apt_table.setItem(idx, 0, QTableWidgetItem(str(r["apartmentID"])))
            self.location_apt_table.setItem(idx, 1, QTableWidgetItem(r["type"] or ""))
            self.location_apt_table.setItem(idx, 2, QTableWidgetItem(f"{float(r['monthlyRent'] or 0):.2f}"))
            self.location_apt_table.setItem(idx, 3, QTableWidgetItem(str(int(r["numberOfRooms"] or 0))))
            status = "Occupied" if int(r["occupancyStatus"] or 0) == 1 else "Available"
            self.location_apt_table.setItem(idx, 4, QTableWidgetItem(status))


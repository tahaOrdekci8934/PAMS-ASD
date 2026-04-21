# Agile PM & Security — Dylan Morgan (24030018): deny access when this panel is not loaded for a maintenance role.
class MaintenancePanel(QWidget):
    def __init__(self, user):

        super().__init__()
        self.user = user
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(outer_layout)

        self.work_widget = self.build_work_orders_panel()
        outer_layout.addWidget(self.work_widget)
  
    def _require_maintenance_staff(self):
        if self.user.get("role") != "maintenance":
            QMessageBox.critical(
                self,
                "Access denied",
                "Only maintenance staff may use this panel.",
            )
            return False
        return True

    def show_work_orders(self):
        # Invoked from sidebar navigation to refresh work orders from the database.
        self.load_work_orders()

    def build_work_orders_panel(self):
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        card = QFrame()
        card.setObjectName("FormCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("My Work Orders")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        filter_row = QHBoxLayout()
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")

        self.work_filter = QComboBox()
        self.work_filter.addItems(["ALL", "PENDING", "IN_PROGRESS", "RESOLVED"])
        self.work_filter.currentTextChanged.connect(self.load_work_orders)

        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.work_filter)
        filter_row.addStretch()

        # Eleven columns including liaison fields; the final column contains workflow controls.
        self.work_table = QTableWidget()
        self.work_table.setColumnCount(11)
        self.work_table.setHorizontalHeaderLabels(
            [
                "Request ID",
                "Apartment",
                "Description",
                "Priority",
                "Status",
                "Date Reported",
                "Scheduled visit",
                "Tenant liaison",
                "Time",
                "Cost",
                "Action",
            ]
        )
        w_hdr = self.work_table.horizontalHeader()
        w_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 10):
            w_hdr.setSectionResizeMode(col, QHeaderView.Stretch)
        w_hdr.setSectionResizeMode(10, QHeaderView.ResizeToContents)
        self.work_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.work_table.setSelectionBehavior(QTableWidget.SelectRows)
        w_vh = self.work_table.verticalHeader()
        w_vh.setVisible(False)
        w_vh.setDefaultSectionSize(52)
        w_vh.setMinimumSectionSize(48)
        self.work_table.setMinimumHeight(320)

        self.work_orders_empty_hint = QLabel(
            "No work orders match the current filter. Try ALL or wait for front desk to log new jobs."
        )
        self.work_orders_empty_hint.setWordWrap(True)
        self.work_orders_empty_hint.setStyleSheet(app_theme.HINT + " background: transparent;")
        self.work_orders_empty_hint.setVisible(False)

        card_layout.addWidget(title)
        card_layout.addLayout(filter_row)
        card_layout.addWidget(self.work_table)
        card_layout.addWidget(self.work_orders_empty_hint)
        outer.addWidget(card)
        container.setLayout(outer)
        return container

    def load_work_orders(self):
        # Filter ALL omits a status predicate; other values match the status column exactly.
        if not self._require_maintenance_staff():
            return
        status_filter = self.work_filter.currentText()
        conn = get_connection()
        cursor = conn.cursor()

        where = ""
        params = []
        if status_filter != "ALL":
            where = " WHERE mr.status = ?"
            params.append(status_filter)

        cursor.execute(
            """
            SELECT
                mr.requestID,
                a.location || ' - ' || COALESCE(a.type,'') AS apartment,
                mr.description,
                mr.priority,
                mr.status,
                mr.dateReported,
                mr.scheduledVisitDate,
                mr.tenantCommunicationNote,
                mr.timeTaken,
                mr.associatedCost,
                mr.resolutionDate
            FROM maintenance_requests mr
            JOIN apartments a ON a.apartmentID = mr.apartmentID
            """
            + where
            + """
            ORDER BY
                CASE mr.priority
                    WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4
                END,
                mr.dateReported DESC
            """,
            params,
        )
        rows = cursor.fetchall()
        conn.close()

        self.work_orders_empty_hint.setVisible(len(rows) == 0)
        self.work_table.setRowCount(len(rows))

        # Priority-based foreground colours to highlight urgency without additional controls.
        priority_colors = {
            "URGENT": QColor(app_theme.C_DANGER),
            "HIGH": QColor(app_theme.C_WARNING),
            "MEDIUM": QColor(app_theme.C_TEXT_MUTED),
            "LOW": QColor(app_theme.C_SUCCESS),
        }
        status_colors = {
            "PENDING": QColor(app_theme.C_WARNING),
            "IN_PROGRESS": QColor(app_theme.C_ACCENT_HOVER),
            "RESOLVED": QColor(app_theme.C_SUCCESS),
        }

        for row_idx, r in enumerate(rows):
            # Local variables per iteration for clarity when constructing row widgets.
            request_id = r["requestID"]
            apartment = r["apartment"]
            description = r["description"] or ""
            short_desc = description[:60] + "..." if len(description) > 60 else description
            priority = r["priority"] or ""
            status = r["status"] or ""
            date_reported = r["dateReported"] or ""
            time_taken = r["timeTaken"]
            assoc_cost = r["associatedCost"]
            resolution_date = r["resolutionDate"] or ""
            scheduled = r["scheduledVisitDate"] or ""
            liaison = r["tenantCommunicationNote"] or ""

            rid_item = QTableWidgetItem(str(request_id))
            rid_item.setToolTip(str(request_id))
            self.work_table.setItem(row_idx, 0, rid_item)
            self.work_table.setItem(row_idx, 1, QTableWidgetItem(apartment or ""))
            self.work_table.setItem(row_idx, 2, QTableWidgetItem(short_desc))

            pr_item = QTableWidgetItem(priority)
            pr_item.setForeground(priority_colors.get(priority, QColor(app_theme.C_TEXT)))
            self.work_table.setItem(row_idx, 3, pr_item)

            st_item = QTableWidgetItem(status)
            st_item.setForeground(status_colors.get(status, QColor(app_theme.C_TEXT)))
            self.work_table.setItem(row_idx, 4, st_item)

            self.work_table.setItem(row_idx, 5, QTableWidgetItem(date_reported))
            self.work_table.setItem(row_idx, 6, QTableWidgetItem(scheduled))

            liaison_short = liaison[:50] + "..." if len(liaison) > 50 else liaison
            lia_item = QTableWidgetItem(liaison_short)
            lia_item.setToolTip(liaison)
            self.work_table.setItem(row_idx, 7, lia_item)

            self.work_table.setItem(row_idx, 8, QTableWidgetItem(str(time_taken) if time_taken is not None else ""))
            self.work_table.setItem(row_idx, 9, QTableWidgetItem(f"{assoc_cost:.2f}" if assoc_cost is not None else ""))

            # Action buttons depend on workflow state: pending allows start and resolve; in-progress allows resolve; resolved allows removal.
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(6, 6, 6, 6)
            action_layout.setSpacing(8)

            btn_geom = (
                "min-height: 32px !important; padding: 6px 10px !important; "
                "font-size: 11px; border-radius: 6px; font-weight: 600; border: none;"
            )

            if status in ("PENDING",):
                # Start transitions the request to IN_PROGRESS without opening the resolution dialog.
                start_btn = QPushButton("Start")
                start_btn.setStyleSheet(
                    f"background-color: {app_theme.C_WARNING}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
                )
                start_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                start_btn.setMinimumHeight(32)
                start_btn.clicked.connect(lambda _, rid=request_id: self.start_request(rid))
                action_layout.addWidget(start_btn)

                resolve_btn = QPushButton("Resolve")
                resolve_btn.setStyleSheet(
                    f"background-color: {app_theme.C_ACCENT}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
                )
                resolve_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                resolve_btn.setMinimumHeight(32)
                resolve_btn.clicked.connect(lambda _, rid=request_id: self.resolve_request(rid))
                action_layout.addWidget(resolve_btn)

            elif status in ("IN_PROGRESS",):
                # In-progress state: resolution dialog collects time, cost, and liaison fields.
                resolve_btn = QPushButton("Resolve")
                resolve_btn.setStyleSheet(
                    f"background-color: {app_theme.C_ACCENT}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
                )
                resolve_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                resolve_btn.setMinimumHeight(32)
                resolve_btn.clicked.connect(lambda _, rid=request_id: self.resolve_request(rid))
                action_layout.addWidget(resolve_btn)

            else:
                # Resolved state: informational label and optional delete for housekeeping.
                view_lbl = QLabel(f"Resolved ({resolution_date})" if resolution_date else "Resolved")
                view_lbl.setStyleSheet(
                    f"color: {app_theme.C_SUCCESS}; font-weight: 600; background: transparent;"
                )
                action_layout.addWidget(view_lbl)
                remove_btn = QPushButton("Remove")
                remove_btn.setStyleSheet(
                    f"background-color: {app_theme.C_DANGER}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
                )
                remove_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                remove_btn.setMinimumHeight(32)
                remove_btn.clicked.connect(
                    lambda _, rid=request_id: self.delete_resolved_work_order(rid)
                )
                action_layout.addWidget(remove_btn)

            action_layout.addStretch()
            action_widget.setLayout(action_layout)
            action_widget.setMinimumHeight(44)
            action_widget.setMinimumWidth(max(action_widget.sizeHint().width(), 80))
            self.work_table.setCellWidget(row_idx, 10, action_widget)
            self.work_table.resizeRowToContents(row_idx)
            if self.work_table.rowHeight(row_idx) < 52:
                self.work_table.setRowHeight(row_idx, 52)

        self.work_table.resizeColumnToContents(0)
        self.work_table.resizeColumnToContents(10)

    def delete_resolved_work_order(self, request_id: str):
        if not self._require_maintenance_staff():
            return
        # Optional deletion of completed work orders after explicit confirmation.
        reply = QMessageBox.question(
            self,
            "Remove work order",
            "Remove this completed work order from the system? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): delete resolved work order row.
        try:
            conn.execute("DELETE FROM maintenance_requests WHERE requestID = ?", (request_id,))
            conn.commit()
            QMessageBox.information(self, "Removed", "Work order removed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
            self.load_work_orders()

    def start_request(self, request_id: str):
        if not self._require_maintenance_staff():
            return
        # Backend & Database — Finn Lennaghan (24024274): status transition PENDING → IN_PROGRESS.
        # Single-column status update; user feedback is provided via a message box only.
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE maintenance_requests SET status = 'IN_PROGRESS' WHERE requestID = ?",
                (request_id,),
            )
            conn.commit()
            QMessageBox.information(self, "Started", "Work order moved to IN_PROGRESS.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not start request:\n{e}")
        finally:
            conn.close()
            self.load_work_orders()

    def resolve_request(self, request_id: str):
        if not self._require_maintenance_staff():
            return
        # Modal dialog captures liaison scheduling, tenant communication note, labour minutes, and cost.
        dialog = QDialog(self)
        dialog.setWindowTitle("Resolve Work Order")
        dialog.setMinimumWidth(420)

        form = QFormLayout()

        visit_date = QDateEdit()
        visit_date.setCalendarPopup(True)
        visit_date.setDate(QDate.currentDate())

        liaison_note = QPlainTextEdit()
        liaison_note.setPlaceholderText("Optional note for tenant liaison / handover…")
        liaison_note.setMaximumHeight(90)

        time_taken = QSpinBox()
        time_taken.setRange(1, 1000000)
        time_taken.setValue(120)

        cost = QDoubleSpinBox()
        cost.setRange(0, 99999999)
        cost.setDecimals(2)
        cost.setValue(250.00)

        form.addRow("Scheduled visit date:", visit_date)
        form.addRow("Tenant communication note:", liaison_note)
        form.addRow("Time taken (minutes):", time_taken)
        form.addRow("Associated cost (£):", cost)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        vbox = QVBoxLayout()
        vbox.addLayout(form)
        vbox.addWidget(buttons)
        dialog.setLayout(vbox)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Persist numeric inputs and set resolutionDate to the current server date within the same update.
        minutes = int(time_taken.value())
        associated_cost = float(cost.value())
        visit_iso = visit_date.date().toString("yyyy-MM-dd")
        note_text = liaison_note.toPlainText().strip()

        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): store resolution time, cost, liaison fields, RESOLVED status.
        try:
            conn.execute(
                """
                UPDATE maintenance_requests
                SET status = 'RESOLVED',
                    resolutionDate = date('now'),
                    scheduledVisitDate = ?,
                    tenantCommunicationNote = ?,
                    timeTaken = ?,
                    associatedCost = ?
                WHERE requestID = ?
                """,
                (visit_iso, note_text or None, minutes, associated_cost, request_id),
            )
            conn.commit()
            QMessageBox.information(self, "Resolved", "Work order marked as RESOLVED.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not resolve request:\n{e}")
        finally:
            conn.close()
            self.load_work_orders()
        # Backend & Database — Finn Lennaghan (24024274): persist PAID status with existence and idempotency checks.
class FinancePanel(QWidget):
         
    def mark_invoice_paid(self, invoice_id: str):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status FROM invoices WHERE invoiceID = ?", (invoice_id,))
            row = cur.fetchone()
            if not row:
                QMessageBox.warning(self, "Not Found", "Invoice not found.")
                return
            if row["status"] == "PAID":
                QMessageBox.information(self, "Already Paid", "This invoice is already marked as paid.")
                return

            conn.execute("UPDATE invoices SET status = 'PAID' WHERE invoiceID = ?", (invoice_id,))
            conn.commit()
            QMessageBox.information(self, "Payment Recorded", f"Invoice {invoice_id} marked as PAID.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not record payment:\n{e}")
        finally:
            conn.close()
            self.load_invoices()
            # Refresh reports so totals stay consistent when navigating between tabs during updates.
            self.load_reports()

    def delete_invoice(self, invoice_id: str, tenant: str, amount, status: str):
        # Confirmation dialog summarises the invoice; on acceptance, delete a single row.
        amt_txt = f"{float(amount):.2f}" if amount is not None else "0.00"
        reply = QMessageBox.question(
            self,
            "Delete invoice",
            f"Permanently remove this invoice from the system?\n\n"
            f"Tenant: {tenant}\n"
            f"Amount: £{amt_txt}\n"
            f"Status: {status}\n"
            f"ID: {invoice_id}\n\n"
            f"This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): delete single invoice row after confirm.
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM invoices WHERE invoiceID = ?", (invoice_id,))
            if not cur.fetchone():
                QMessageBox.warning(self, "Not found", "That invoice no longer exists.")
                return
            cur.execute("DELETE FROM invoices WHERE invoiceID = ?", (invoice_id,))
            conn.commit()
            QMessageBox.information(self, "Invoice removed", "The invoice has been deleted.")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
            self.load_invoices()
            self.load_reports()

    def build_reports_panel(self):
        # Reports tab: headline metrics, bulk invoice-management actions, and per-location breakdown table.
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        card = QFrame()
        card.setObjectName("FormCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("Financial Reports")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        # Summary metric labels; load_reports assigns text from aggregate queries.
        summary_row = QHBoxLayout()
        self.collected_lbl = QLabel("Collected: £0.00")
        self.pending_lbl = QLabel("Pending: £0.00")
        self.late_lbl = QLabel("Late invoices: 0")

        summary_metric = (
            f"color: {app_theme.C_TEXT}; font-size: 14px; font-weight: 600; background: transparent;"
        )
        for lbl in [self.collected_lbl, self.pending_lbl, self.late_lbl]:
            lbl.setStyleSheet(summary_metric)
            summary_row.addWidget(lbl)

        summary_row.addStretch()

        # Section title preceding bulk data-management actions.
        data_mgmt_lbl = QLabel("Invoice & payment history")
        data_mgmt_lbl.setStyleSheet(app_theme.SECTION_TITLE + "background: transparent;")

        bulk_row = QHBoxLayout()
        bulk_row.setSpacing(10)
        self.clear_paid_btn = QPushButton("Remove all paid invoices")
        self.clear_paid_btn.setToolTip(
            "Deletes every invoice marked PAID (clears recorded payment history). Unpaid invoices are kept."
        )
        self.clear_paid_btn.clicked.connect(self.delete_all_paid_invoices)
        self.clear_all_inv_btn = QPushButton("Remove all invoices")
        self.clear_all_inv_btn.setToolTip("Deletes every invoice in the database, including unpaid.")
        self.clear_all_inv_btn.clicked.connect(self.delete_all_invoices)
        bulk_row.addWidget(self.clear_paid_btn)
        bulk_row.addWidget(self.clear_all_inv_btn)
        bulk_row.addStretch()

        bulk_hint = QLabel(
            "These actions permanently remove rows from the invoices table. Use with care in production."
        )
        bulk_hint.setWordWrap(True)
        bulk_hint.setStyleSheet(app_theme.HINT + "background: transparent;")

        # Per-location financial breakdown table.
        self.location_table = QTableWidget()
        self.location_table.setColumnCount(4)
        self.location_table.setHorizontalHeaderLabels(
            ["Location", "Collected (£)", "Pending (£)", "Late Count"]
        )
        self.location_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.location_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.location_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.location_table.verticalHeader().setVisible(False)
        self.location_table.setMinimumHeight(300)

        card_layout.addWidget(title)
        card_layout.addLayout(summary_row)
        card_layout.addWidget(data_mgmt_lbl)
        card_layout.addLayout(bulk_row)
        card_layout.addWidget(bulk_hint)
        card_layout.addWidget(self.location_table)
        outer.addWidget(card)
        container.setLayout(outer)
        return container

    def load_reports(self):
        # Summary labels aggregate all invoices; the table groups the same measures by apartment city.
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status = 'PAID' THEN amount ELSE 0 END), 0) AS collected,
                COALESCE(SUM(CASE WHEN status = 'UNPAID' THEN amount ELSE 0 END), 0) AS pending,
                COALESCE(SUM(CASE WHEN status = 'UNPAID' AND date(dueDate) < date('now') THEN 1 ELSE 0 END), 0) AS lateCount
            FROM invoices
            """
        )
        summary = cursor.fetchone()

        # Conditional aggregates convert invoice status into monetary and count totals for the summary row.
        collected = float(summary["collected"] or 0)
        pending = float(summary["pending"] or 0)
        late_count = int(summary["lateCount"] or 0)

        self.collected_lbl.setText(f"Collected: £{collected:.2f}")
        self.pending_lbl.setText(f"Pending: £{pending:.2f}")
        self.late_lbl.setText(f"Late invoices: {late_count}")

        # Follow-on query groups collected, pending, and late counts by apartment location.
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
        rows = cursor.fetchall()
        conn.close()

        self.location_table.setRowCount(len(rows))
        for row_idx, r in enumerate(rows):
            location = r["location"]
            collected_amt = float(r["collected"] or 0)
            pending_amt = float(r["pending"] or 0)
            late_cnt = int(r["lateCount"] or 0)

            self.location_table.setItem(row_idx, 0, QTableWidgetItem(location or ""))
            self.location_table.setItem(row_idx, 1, QTableWidgetItem(f"{collected_amt:.2f}"))
            self.location_table.setItem(row_idx, 2, QTableWidgetItem(f"{pending_amt:.2f}"))
            self.location_table.setItem(row_idx, 3, QTableWidgetItem(str(late_cnt)))

    def delete_all_paid_invoices(self):
        # Pre-count matching rows so the confirmation dialog states the exact deletion scope.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS c FROM invoices WHERE status = 'PAID'")
        n = int(cursor.fetchone()["c"] or 0)
        conn.close()
        if n <= 0:
            QMessageBox.information(self, "Nothing to remove", "There are no paid invoices to delete.")
            return
        reply = QMessageBox.question(
            self,
            "Remove paid invoices",
            f"This will permanently delete {n} paid invoice(s). Unpaid invoices will not be removed.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): bulk delete paid invoices only.
        try:
            conn.execute("DELETE FROM invoices WHERE status = 'PAID'")
            conn.commit()
            QMessageBox.information(self, "Done", f"Removed {n} paid invoice(s).")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
            self.load_reports()
            self.load_invoices()

    def delete_all_invoices(self):
        # Same confirmation pattern as paid-only bulk delete, applied to the entire invoice table.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS c FROM invoices")
        n = int(cursor.fetchone()["c"] or 0)
        conn.close()
        if n <= 0:
            QMessageBox.information(self, "Nothing to remove", "There are no invoices to delete.")
            return
        reply = QMessageBox.question(
            self,
            "Remove all invoices",
            f"This will permanently delete all {n} invoice(s), including unpaid and late.\n\n"
            f"This cannot be undone. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        conn = get_connection()
        # Backend & Database — Finn Lennaghan (24024274): bulk delete all invoices (destructive).
        try:
            conn.execute("DELETE FROM invoices")
            conn.commit()
            QMessageBox.information(self, "Done", f"Removed {n} invoice(s).")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            conn.close()
            self.load_reports()
            self.load_invoices()


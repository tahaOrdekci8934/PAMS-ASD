# UI/UX & Frontend — Taha Ordekci (25013992) (finance PyQt screens: invoices, reports, filters, actions).
# Finance: list invoices, mark paid, delete rows, simple reports / bulk delete.
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QMessageBox,
    QHeaderView,
    QStackedWidget,
    QFrame,
    QSizePolicy,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from datetime import date as _date

from database.db_connection import get_connection
from views import app_theme


class FinancePanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user

        # Stacked views: index 0 invoices, index 1 financial reports.
        self.stack = QStackedWidget()
        self.invoices_widget = self.build_invoices_panel()
        self.reports_widget = self.build_reports_panel()

        self.stack.addWidget(self.invoices_widget)
        self.stack.addWidget(self.reports_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def show_invoices(self):
        # Reload data on each visit so invoice status reflects the latest database state.
        self.stack.setCurrentIndex(0)
        self.load_invoices()

    def show_reports(self):
        self.stack.setCurrentIndex(1)
        self.load_reports()

    def build_invoices_panel(self):
        container = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(30, 30, 30, 30)
        outer.setSpacing(16)

        # FormCard object name selects the global stylesheet card treatment.
        card = QFrame()
        card.setObjectName("FormCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        title = QLabel("Invoices & Payments")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet(app_theme.PAGE_TITLE + "background: transparent;")

        filter_row = QHBoxLayout()
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet(app_theme.FIELD_LABEL + "background: transparent;")

        self.invoices_filter = QComboBox()
        self.invoices_filter.addItems(["ALL", "UNPAID", "PAID", "LATE"])
        self.invoices_filter.currentTextChanged.connect(self.load_invoices)

        filter_row.addWidget(filter_label)
        filter_row.addWidget(self.invoices_filter)
        filter_row.addStretch()

        # Late invoice counter and notification control; the button is enabled only when the late count is positive.
        late_row = QHBoxLayout()
        self.late_alert_lbl = QLabel("Late invoices: 0")
        self.late_alert_lbl.setStyleSheet(
            f"color: {app_theme.C_DANGER}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        self.notify_btn = QPushButton("Notify Late Tenants")
        self.notify_btn.setEnabled(False)
        self.notify_btn.clicked.connect(self.notify_late_tenants)
        late_row.addWidget(self.late_alert_lbl)
        late_row.addStretch()
        late_row.addWidget(self.notify_btn)

        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(7)
        self.invoices_table.setHorizontalHeaderLabels(
            ["Invoice ID", "Tenant", "Apartment", "Amount (£)", "Due Date", "Status", "Action"]
        )
        inv_hdr = self.invoices_table.horizontalHeader()
        inv_hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 6):
            inv_hdr.setSectionResizeMode(col, QHeaderView.Stretch)
        inv_hdr.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.invoices_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectRows)
        inv_vh = self.invoices_table.verticalHeader()
        inv_vh.setVisible(False)
        inv_vh.setDefaultSectionSize(52)
        inv_vh.setMinimumSectionSize(48)
        self.invoices_table.setMinimumHeight(300)

        card_layout.addWidget(title)
        card_layout.addLayout(filter_row)
        card_layout.addLayout(late_row)
        card_layout.addWidget(self.invoices_table)
        inv_hint = QLabel(
            "Use Delete on a row to remove that invoice from the register. Paid rows remove payment history for that bill."
        )
        inv_hint.setWordWrap(True)
        inv_hint.setStyleSheet(app_theme.HINT + "background: transparent;")
        card_layout.addWidget(inv_hint)
        outer.addWidget(card)
        container.setLayout(outer)
        return container

    def load_invoices(self):
        # Status filter drives the WHERE clause; ALL selects the full invoice set.
        status_filter = self.invoices_filter.currentText()
        conn = get_connection()
        cursor = conn.cursor()

        # Join invoices to leases, tenants, and apartments for display columns.
        # Date comparisons assume ISO-8601 (yyyy-mm-dd) due date strings in SQLite.
        base_query = """
            SELECT
                i.invoiceID,
                t.name AS tenantName,
                a.location || ' - ' || COALESCE(a.type,'') AS apartment,
                i.amount,
                i.dueDate,
                i.status
            FROM invoices i
            JOIN lease_agreements la ON la.leaseID = i.leaseID
            JOIN tenants t ON t.tenantID = la.tenantID
            JOIN apartments a ON a.apartmentID = la.apartmentID
        """

        # Construct the WHERE clause using parameter binding rather than string concatenation.
        where = ""
        params = []
        if status_filter == "UNPAID":
            where = " WHERE i.status = ?"
            params.append("UNPAID")
        elif status_filter == "PAID":
            where = " WHERE i.status = ?"
            params.append("PAID")
        elif status_filter == "LATE":
            where = " WHERE i.status = 'UNPAID' AND date(i.dueDate) < date('now')"

        order_by = " ORDER BY i.status DESC, date(i.dueDate) ASC"

        cursor.execute(base_query + where + order_by, params)
        invoices = cursor.fetchall()

        # Secondary query: count of unpaid invoices past due date for the alert label and notify action.
        cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM invoices
            WHERE status = 'UNPAID' AND date(dueDate) < date('now')
            """
        )
        late_cnt = int(cursor.fetchone()["cnt"] or 0)
        self.late_alert_lbl.setText(f"Late invoices: {late_cnt}")
        self.notify_btn.setEnabled(late_cnt > 0)

        conn.close()

        # One row per invoice; the final column hosts row-level action widgets.
        self.invoices_table.setRowCount(len(invoices))
        for row, inv in enumerate(invoices):
            invoice_id = inv["invoiceID"]
            tenant = inv["tenantName"]
            apartment = inv["apartment"]
            amount = inv["amount"]
            due_date = inv["dueDate"]
            status = inv["status"]

            id_item = QTableWidgetItem(str(invoice_id))
            # Tooltip carries the full identifier when the column width truncates the text.
            id_item.setToolTip(str(invoice_id))
            self.invoices_table.setItem(row, 0, id_item)
            self.invoices_table.setItem(row, 1, QTableWidgetItem(tenant or ""))
            self.invoices_table.setItem(row, 2, QTableWidgetItem(apartment or ""))
            self.invoices_table.setItem(row, 3, QTableWidgetItem(f"{amount:.2f}" if amount is not None else "0.00"))
            self.invoices_table.setItem(row, 4, QTableWidgetItem(due_date or ""))

            status_item = QTableWidgetItem(status or "")
            # Colour coding: unpaid and past due use the danger palette; unpaid with future due date use warning.
            is_late = False
            if status == "UNPAID" and due_date:
                try:
                    is_late = _date.fromisoformat(str(due_date)) < _date.today()
                except ValueError:
                    is_late = False

            if status_item.text() == "UNPAID":
                status_item.setForeground(
                    QColor(app_theme.C_DANGER) if is_late else QColor(app_theme.C_WARNING)
                )
            if status_item.text() == "PAID":
                status_item.setForeground(QColor(app_theme.C_SUCCESS))
            self.invoices_table.setItem(row, 5, status_item)

            # Action cell: read-only Paid label, or Mark Paid plus Delete for open invoices.
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(6, 6, 6, 6)
            action_layout.setSpacing(8)

            btn_geom = (
                "min-height: 32px !important; padding: 6px 12px !important; "
                "font-size: 11px; border-radius: 6px; font-weight: 600; border: none;"
            )

            if status == "PAID":
                paid_lbl = QLabel("Paid")
                paid_lbl.setStyleSheet(
                    f"color: {app_theme.C_SUCCESS}; font-weight: 600; background: transparent;"
                )
                action_layout.addWidget(paid_lbl)
            else:
                pay_btn = QPushButton("Mark Paid")
                pay_btn.setStyleSheet(
                    f"background-color: {app_theme.C_SUCCESS}; color: {app_theme.C_TEXT}; {btn_geom}"
                )
                pay_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
                pay_btn.setMinimumHeight(32)
                pay_btn.clicked.connect(lambda _, iid=invoice_id: self.mark_invoice_paid(iid))
                action_layout.addWidget(pay_btn)

            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet(
                f"background-color: {app_theme.C_DANGER}; color: {app_theme.C_ON_ACCENT}; {btn_geom}"
            )
            del_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            del_btn.setMinimumHeight(32)
            del_btn.clicked.connect(
                lambda _, iid=invoice_id, tn=tenant or "", am=amount, st=status or "":
                self.delete_invoice(iid, tn, am, st)
            )
            action_layout.addWidget(del_btn)

            action_layout.addStretch()
            action_widget.setLayout(action_layout)
            action_widget.setMinimumHeight(44)
            action_widget.setMinimumWidth(max(action_widget.sizeHint().width(), 220))
            self.invoices_table.setCellWidget(row, 6, action_widget)
            self.invoices_table.resizeRowToContents(row)
            if self.invoices_table.rowHeight(row) < 52:
                self.invoices_table.setRowHeight(row, 52)

        self.invoices_table.resizeColumnToContents(0)
        self.invoices_table.resizeColumnToContents(6)

    def notify_late_tenants(self):
        # No external messaging integration: emulate notification by counting distinct affected tenants.
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(DISTINCT la.tenantID) AS tenantCount
            FROM invoices i
            JOIN lease_agreements la ON la.leaseID = i.leaseID
            WHERE i.status = 'UNPAID' AND date(i.dueDate) < date('now')
            """
        )
        tenant_count = int(cursor.fetchone()["tenantCount"] or 0)
        conn.close()

        if tenant_count <= 0:
            QMessageBox.information(self, "No Late Payments", "There are no late unpaid invoices to notify.")
            return

        QMessageBox.information(
            self,
            "Late Payment Notifications",
            f"Notifications sent (emulated) to {tenant_count} tenant(s) with late unpaid invoices.",
        )

    def mark_invoice_paid(self, invoice_id: str):
        # Backend & Database — Finn Lennaghan (24024274): persist PAID status with existence and idempotency checks.
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


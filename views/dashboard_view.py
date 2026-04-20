#Agile PM & Security — Dylan Morgan (24030018): RBAC — which panel class is loaded for each staff role.
#Deferred imports reduce startup cost and avoid loading unused role modules.
def _build_panel_for_role(self, role):
    if role == 'admin':
        from views.admin_panel import AdminPanel
        panel = AdminPanel(self.user)
        self._panel_ref = panel
        return panel

    elif role == 'front_desk':
        from views.front_desk_panel import FrontDeskPanel
        panel = FrontDeskPanel(self.user)
        self._panel_ref = panel
        return panel

    elif role == 'finance':
        from views.finance_panel import FinancePanel
        panel = FinancePanel(self.user)
        self._panel_ref = panel
        return panel

    elif role == 'maintenance':
        from views.maintenance_panel import MaintenancePanel
        panel = MaintenancePanel(self.user)
        self._panel_ref = panel
        return panel

    elif role == 'manager':
        from views.manager_panel import ManagerPanel
        panel = ManagerPanel(self.user)
        self._panel_ref = panel
        return panel

    else:
        # Fallback when the database contains a role not implemented in this client version.
        return self._placeholder(f"Panel for role '{role}' is not implemented.")

def _placeholder(self, text):
    # Centred placeholder content for unsupported roles instead of raising an unhandled exception.
    w = QWidget()
    layout = QVBoxLayout()
    layout.setAlignment(Qt.AlignCenter)
    lbl = QLabel(text)
    lbl.setStyleSheet(HINT + "font-size: 15px; background: transparent;")
    lbl.setAlignment(Qt.AlignCenter)
    layout.addWidget(lbl)
    w.setLayout(layout)
    return w

def switchpanel(self, index):
    # Agile PM & Security — Dylan Morgan (24030018): RBAC — sidebar index + role decide which sub-view is active.
    # Invoked from sidebar navigation to activate the selected sub-view within the role panel.
    # Each panel implements show* methods that refresh bound data sources.
    role = self.user['role']

    if role == 'admin':
        if index == 0:
            self._panel_ref.show_users()
        elif index == 1:
            self._panel_ref.show_apartments()
        elif index == 2:
            self._panel_ref.show_leases()

    elif role == 'front_desk':
        if index == 0:
            self._panel_ref.show_tenants()
        elif index == 1:
            self._panel_ref.show_maintenance()

    elif role == 'finance':
        if index == 0:
            self._panel_ref.show_invoices()
        elif index == 1:
            self._panel_ref.show_reports()

    elif role == 'maintenance':
        if index == 0:
            self._panel_ref.show_work_orders()

    elif role == 'manager':
        if index == 0:
            self._panel_ref.show_occupancy()
        elif index == 1:
            self._panel_ref.show_reports()
        elif index == 2:
            self._panel_ref.show_locations()

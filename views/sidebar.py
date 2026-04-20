#Agile PM & Security — Dylan Morgan (24030018): RBAC — each role sees a different set of menu actions.
#show_panel returns a zero-argument callable for use as a Qt signal slot.
        if role == 'admin':
            return [
                ("  User Management",       self.show_panel(0)),
                ("  Apartment Management",  self.show_panel(1)),
                ("  Lease Agreements",     self.show_panel(2)),
            ]
          
        elif role == 'front_desk':
            return [
                ("  Tenant Registration",   self.show_panel(0)),
                ("  Maintenance Requests",  self.show_panel(1)),
            ]
          
        elif role == 'finance':
            return [
                ("  Invoices & Payments",   self.show_panel(0)),
                ("  Financial Reports",     self.show_panel(1)),
            ]
          
        elif role == 'maintenance':
            return [
                ("  My Work Orders",        self.show_panel(0)),
            ]
          
        elif role == 'manager':
            return [
                ("  Occupancy Overview",    self.show_panel(0)),
                ("  Performance Reports",   self.show_panel(1)),
                ("  Manage Locations",      self.show_panel(2)),
            ]
          
        return []

    def show_panel(self, index):
        # Factory function: each handler closes over the correct panel index.
        def handler():
            self.set_active(index)
            self.dashboard.switch_panel(index)
        return handler

    def set_active(self, index):
        # Mutually exclusive checkable buttons: exactly one appears active at any time.
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

    def logout(self):
        # Present a new login window and close the authenticated dashboard session.
        from views.login_view import LoginView
        self.login = LoginView()
        self.login.show()
        self.dashboard.close()

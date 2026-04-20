
# UI/UX & Frontend — Taha Ordekci (25013992) (sidebar look & feel, spacing, logout control).
# Left navigation: which buttons show depends on the logged-in role.
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                              QPushButton, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from views.app_theme import sidebar_stylesheet, C_ACCENT_HOVER, FIELD_LABEL, HINT


class Sidebar(QWidget):
    def __init__(self, user, dashboard):
        super().__init__()
        self.user = user
        # Reference to DashboardView for panel switching and coordinated window closure on logout.
        self.dashboard = dashboard
        self.setObjectName("AppSidebar")
        self.setFixedWidth(248)
        self.setStyleSheet(sidebar_stylesheet())
        self.init_ui()

    def init_ui(self):
        # Vertical layout: branding, signed-in user details, navigation buttons, spacer, logout control.
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(6)

        app_title = QLabel("PAMS")
        app_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        app_title.setStyleSheet(
            f"color: {C_ACCENT_HOVER}; font-size: 18px; font-weight: bold; "
            f"padding: 10px 10px 4px 10px; background: transparent;"
        )

        user_name = QLabel(self.user['name'])
        user_name.setStyleSheet(FIELD_LABEL + "padding-left: 10px; background: transparent;")

        role_label = QLabel(self.user['role'].replace('_', ' ').title())
        role_label.setStyleSheet(HINT + "padding-left: 10px; background: transparent;")

        layout.addWidget(app_title)
        layout.addWidget(user_name)
        layout.addWidget(role_label)
        layout.addSpacing(20)

        # Role-specific list of navigation labels and associated handler callables.
        role = self.user['role']
        buttons = self.get_buttons_for_role(role)

        # Retain button references so set_active can update the checked visual state.
        self.nav_buttons = []
        for label, handler in buttons:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("nav", True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # First navigation entry is selected when the dashboard initialises.
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        # Expanding spacer pushes the logout control to the foot of the sidebar.
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        logout_btn = QPushButton("Sign out")
        logout_btn.setProperty("logout", True)
        logout_btn.setCheckable(False)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)

        self.setLayout(layout)

    def get_buttons_for_role(self, role):
        # Agile PM & Security — Dylan Morgan (24030018): RBAC — each role sees a different set of menu actions.
        # show_panel returns a zero-argument callable for use as a Qt signal slot.
        if role == 'admin':
            return [
                (" User Management",       self.show_panel(0)),
                (" Apartment Management",  self.show_panel(1)),
                (" Lease Agreements",     self.show_panel(2)),
            ]
        elif role == 'front_desk':
            return [
                (" Tenant Registration",   self.show_panel(0)),
                (" Maintenance Requests",  self.show_panel(1)),
            ]
        elif role == 'finance':
            return [
                (" Invoices & Payments",   self.show_panel(0)),
                (" Financial Reports",     self.show_panel(1)),
            ]
        elif role == 'maintenance':
            return [
                (" My Work Orders",        self.show_panel(0)),
            ]
        elif role == 'manager':
            return [
                (" Occupancy Overview",    self.show_panel(0)),
                (" Performance Reports",   self.show_panel(1)),
                (" Manage Locations",      self.show_panel(2)),
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
>>>>>>> dfdbc53f9070b72cab4c5a879809885ec738ff59

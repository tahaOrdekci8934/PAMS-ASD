#Backend & Database — Finn Lennaghan (24024274): credential lookup (users table, hashed password).
#Look up user by email + hashed password (plain password is never stored).
conn = get_connection()
cursor = conn.cursor()
hashed = hash_password(password)
cursor.execute(
    "SELECT * FROM users WHERE email = ? AND password = ?",
    (email, hashed)
)
user = cursor.fetchone()
conn.close()

#QA — Wayne Tong (24017066): optional isolated login smoke test; production entry point is main.py.
#Direct execution applies the same database initialisation and stylesheet as main.py, then shows login only.
if user:
    initialize_db()
    app = QApplication(sys.argv)
    from views.app_theme import get_application_stylesheet

    app.setStyleSheet(get_applicationstylesheet())
    window = LoginView()
    window.show()
    sys.exit(app.exec())

# Agile Project Manager & Security Coordinator — Dylan Morgan (24030018) (RBAC: authenticated user’s role drives next screen).
# Login screen: email + password, load user from DB, open the dashboard for that role.
import sys
import os

# Ensures package imports resolve when this module is executed directly (not only via main.py).
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QHBoxLayout,
                             QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database.db_connection import get_connection, hash_password, initialize_db
from views.form_validators import is_valid_email
from views import app_theme


class LoginView(QWidget):
    def __init__(self):
        super().__init__()
        # Fixed window dimensions keep the login card centred and consistent across displays.
        self.setWindowTitle("PAMS - Sign in")
        self.setFixedSize(480, 700)
        self.init_ui()
    def init_ui(self):
        # Vertical stretch distributes space so the card sits slightly above the vertical centre.
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)
        main_layout.addStretch(1)
        # Card frame containing title, fields, and primary action (LoginCard style in app_theme).
        card = QFrame()
        card.setObjectName("LoginCard")
        card.setMinimumWidth(380)
        card.setMaximumWidth(420)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(14)
        # Application title and subtitle labels.
        title = QLabel("PAMS")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 26, QFont.Bold))
        title.setStyleSheet(
            f"color: {app_theme.C_ACCENT_HOVER}; font-size: 26px; font-weight: bold; background: transparent;"
        )
        subtitle = QLabel("Paragon Apartment Management System")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(app_theme.SUBTITLE + " background: transparent;")
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("LoginDivider")
        line.setFixedHeight(1)

        # Email field group: label, single-line input, and format hint.
        email_label = QLabel("Work email")
        email_label.setStyleSheet(app_theme.FIELD_LABEL + " background: transparent;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@paragon-pams.uk")

        email_hint = QLabel("Use a valid work email (include '@').")
        email_hint.setWordWrap(True)
        email_hint.setStyleSheet(app_theme.HINT + " background: transparent;")

        pass_label = QLabel("Password")
        pass_label.setStyleSheet(app_theme.FIELD_LABEL + " background: transparent;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)

        # Password policy text matches the Admin user-creation requirements.
        pass_hint = QLabel(
            "Staff accounts use strong passwords (8+ characters, upper and lower case, "
            "a number, and a symbol). New users created in Admin follow the same rules."
        )
        pass_hint.setWordWrap(True)
        pass_hint.setStyleSheet(app_theme.HINT + " background: transparent;")

        self.login_btn = QPushButton("Sign in")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.handle_login)

        # Return key in the password field triggers the same handler as the Sign in button.
        self.password_input.returnPressed.connect(self.handle_login)

        # Demonstration account list for evaluator access after database initialisation.
        hint = QLabel(
            "Example accounts (run the app once so the database initialises):\n"
            "• Front desk — sarah.mitchell@paragon-pams.uk / Pams#Desk2026!\n"
            "• Finance — james.okonkwo@paragon-pams.uk / Pams#Finance2026!\n"
            "• Maintenance — priya.sharma@paragon-pams.uk / Pams#Maint2026!\n"
            "• Admin — marcus.webb@paragon-pams.uk / Pams#Admin2026!\n"
            "• Manager — elena.rossi@paragon-pams.uk / Pams#Mgr2026!"
        )
        hint.setAlignment(Qt.AlignLeft)
        hint.setWordWrap(True)
        hint.setStyleSheet(app_theme.HINT + " background: transparent; font-size: 10px;")

        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(4)
        card_layout.addWidget(line)
        card_layout.addSpacing(8)
        card_layout.addWidget(email_label)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(email_hint)
        card_layout.addWidget(pass_label)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(pass_hint)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.login_btn)
        card_layout.addSpacing(6)
        card_layout.addWidget(hint)

        card.setLayout(card_layout)
        main_layout.addWidget(card, 0, Qt.AlignHCenter)
        main_layout.addStretch(2)

        self.setLayout(main_layout)

    def handle_login(self):
        # Normalise email to lowercase for consistent lookup against stored values.
        email = self.email_input.text().strip().lower()
        password = self.password_input.text().strip()

        # Validate non-empty credentials before opening a database connection.
        if not email or not password:
            QMessageBox.warning(
                self,
                "Required fields",
                "Please enter both your email address and password.",
            )
            return

        if not is_valid_email(email):
            QMessageBox.warning(
                self,
                "Invalid email",
                "Please enter a valid email address (it must include '@', e.g. name@example.com).",
            )
            return

            # Agile PM & Security — Dylan Morgan (24030018): pass role into dashboard so RBAC panels load correctly.
            self.open_dashboard(dict(user))
        else:
            QMessageBox.critical(
                self,
                "Sign-in failed",
                "The email or password you entered is incorrect. Please try again.",
            )
            self.password_input.clear()

# Agile & security coordination (RBAC in code, sprint evidence in Git) — Dylan Morgan (24030018)
import sys
from PyQt5.QtWidgets import QApplication

# Application modules: database initialisation and the entry screen.
from database.db_connection import initialize_db
from views.app_theme import get_application_stylesheet
from views.login_view import LoginView

if __name__ == "__main__":
    # UI/UX & Frontend — Taha Ordekci (25013992): Qt app shell, global stylesheet, first window.
    app = QApplication(sys.argv)
    app.setStyleSheet(get_application_stylesheet())
    window = LoginView()
    window.show()
    
    # Placeholder for database init and QA exit logic
    pass
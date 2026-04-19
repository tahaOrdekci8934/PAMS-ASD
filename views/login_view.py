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
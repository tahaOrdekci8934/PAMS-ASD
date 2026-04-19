        # Backend & Database — Finn Lennaghan (24024274): credential lookup (users table, hashed password).
        # Look up user by email + hashed password (plain password is never stored).
        conn = get_connection()
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, hashed)
        )
        user = cursor.fetchone()
        conn.close()

        if user:

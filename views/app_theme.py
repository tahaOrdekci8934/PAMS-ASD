# UI/UX & Frontend — Taha Ordekci (25013992) (global Qt styles, palette, shared label tokens).
# Colours and Qt stylesheet strings so every screen looks the same (dark theme).

# Primary interface colour constants.
C_BG = "#0d1117"
C_BG_ELEVATED = "#161b22"
C_BG_INPUT = "#1c2128"
C_BG_MUTED = "#21262d"
C_BORDER = "#30363d"
C_BORDER_FOCUS = "#388bfd"
C_TEXT = "#e6edf3"
C_TEXT_MUTED = "#8b949e"
C_TEXT_DIM = "#6e7681"
C_ACCENT = "#388bfd"
C_ACCENT_HOVER = "#58a6ff"
C_ACCENT_PRESSED = "#1f6feb"
C_ON_ACCENT = "#0d1117"
C_DANGER = "#f85149"
C_DANGER_HOVER = "#ff7b72"
C_SUCCESS = "#3fb950"
C_WARNING = "#d29922"

# Reusable QLabel style fragments (append "background: transparent;" on coloured panel backgrounds).
PAGE_TITLE = f"color: {C_ACCENT_HOVER}; font-size: 22px; font-weight: bold; letter-spacing: -0.3px;"
SECTION_TITLE = f"color: {C_TEXT_MUTED}; font-size: 13px; font-weight: 600;"
FIELD_LABEL = f"color: {C_TEXT_MUTED}; font-size: 12px;"
HINT = f"color: {C_TEXT_DIM}; font-size: 11px;"
SUBTITLE = f"color: {C_TEXT_MUTED}; font-size: 12px;"


def get_application_stylesheet() -> str:
    # Global widget rules covering buttons, tables, inputs, and common containers.
    return f"""
    /* --- Default text and window background --- */
    QWidget {{
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
        color: {C_TEXT};
        background-color: {C_BG};
    }}

    /* --- Pop-up dialogs use same dark background --- */
    QMainWindow, QDialog {{
        background-color: {C_BG};
    }}

    QLabel {{
        background-color: transparent;
        color: {C_TEXT};
    }}

    /* --- Typed inputs: grey box, rounded corners, blue when focused --- */
    QLineEdit, QTextEdit, QPlainTextEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        border-radius: 6px;
        padding: 8px 10px;
        min-height: 18px;
        selection-background-color: {C_ACCENT};
        selection-color: {C_ON_ACCENT};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus {{
        border: 1px solid {C_BORDER_FOCUS};
    }}

    /* --- Drop-down arrow area for combo boxes --- */
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QComboBox::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {C_TEXT_MUTED};
        margin-right: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT};
        border: 1px solid {C_BORDER};
        selection-background-color: {C_BG_MUTED};
        selection-color: {C_ACCENT_HOVER};
        outline: none;
    }}

    /* --- Primary buttons (blue); disabled state is greyed out --- */
    QPushButton {{
        background-color: {C_ACCENT};
        color: {C_ON_ACCENT};
        border: none;
        border-radius: 6px;
        padding: 9px 18px;
        font-weight: 600;
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {C_ACCENT_HOVER};
        color: {C_ON_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: {C_ACCENT_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: {C_BG_MUTED};
        color: {C_TEXT_DIM};
    }}

    /* --- Data tables: striped rows, thin grid, rounded border --- */
    QTableWidget {{
        background-color: {C_BG_ELEVATED};
        alternate-background-color: {C_BG_INPUT};
        color: {C_TEXT};
        gridline-color: {C_BORDER};
        border: 1px solid {C_BORDER};
        border-radius: 8px;
    }}
    QTableWidget::item {{
        padding: 6px 8px;
    }}
    QTableWidget::item:selected {{
        background-color: {C_BG_MUTED};
        color: {C_ACCENT_HOVER};
    }}

    /* --- Column titles row --- */
    QHeaderView::section {{
        background-color: {C_BG_INPUT};
        color: {C_TEXT_MUTED};
        padding: 10px 8px;
        border: none;
        border-bottom: 2px solid {C_BORDER_FOCUS};
        font-weight: 600;
        font-size: 12px;
    }}

    /* --- Scroll areas and thin scroll bars --- */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollBar:vertical {{
        background: {C_BG_ELEVATED};
        width: 10px;
        border-radius: 5px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {C_BORDER};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C_TEXT_MUTED};
    }}

    /* --- Card panels used inside finance / front desk / manager --- */
    QFrame#FormCard {{
        background-color: {C_BG_ELEVATED};
        border: 1px solid {C_BORDER};
        border-radius: 10px;
    }}

    /* --- Login screen centre card --- */
    QFrame#LoginCard {{
        background-color: {C_BG_ELEVATED};
        border: 1px solid {C_BORDER};
        border-radius: 14px;
    }}

    QFrame#LoginDivider {{
        background-color: {C_BORDER};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    """


def sidebar_stylesheet() -> str:
    # Sidebar-specific button styling; other regions use the global button rules above.
    return f"""
    /* --- Left strip background --- */
    QWidget#AppSidebar {{
        background-color: {C_BG_ELEVATED};
        border-right: 1px solid {C_BORDER};
    }}
    QWidget#AppSidebar QLabel {{
        background-color: transparent;
    }}
    /* --- Menu buttons: transparent until hover / selected --- */
    QWidget#AppSidebar QPushButton[nav="true"] {{
        text-align: left;
        padding: 10px 14px;
        border: none;
        border-radius: 8px;
        background-color: transparent;
        color: {C_TEXT_MUTED};
        font-weight: normal;
    }}
    QWidget#AppSidebar QPushButton[nav="true"]:hover {{
        background-color: {C_BG_MUTED};
        color: {C_TEXT};
    }}
    QWidget#AppSidebar QPushButton[nav="true"]:checked {{
        background-color: {C_BG_MUTED};
        color: {C_ACCENT_HOVER};
        font-weight: bold;
    }}
    /* --- Logout: outline style so it looks less like a main action --- */
    QWidget#AppSidebar QPushButton[logout="true"] {{
        background-color: transparent;
        color: {C_DANGER};
        border: 1px solid {C_DANGER};
        padding: 10px 14px;
        font-weight: 600;
    }}
    QWidget#AppSidebar QPushButton[logout="true"]:hover {{
        background-color: {C_DANGER};
        color: {C_ON_ACCENT};
    }}
    """

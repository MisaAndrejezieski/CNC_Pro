"""Estilos modernos para a interface"""


def apply_style(app):
    """Aplica estilo escuro moderno ao aplicativo"""
    
    style = """
    /* Estilo global */
    QMainWindow {
        background-color: #1e1e1e;
    }
    
    QWidget {
        background-color: #252526;
        color: #d4d4d4;
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        font-size: 10pt;
    }
    
    /* Botões */
    QPushButton {
        background-color: #0e639c;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        color: white;
        font-weight: bold;
    }
    
    QPushButton:hover {
        background-color: #1177bb;
    }
    
    QPushButton:pressed {
        background-color: #0a4d74;
    }
    
    QPushButton:disabled {
        background-color: #3e3e42;
        color: #6e6e6e;
    }
    
    /* Botão secundário */
    QPushButton[secondary="true"] {
        background-color: #3e3e42;
    }
    
    QPushButton[secondary="true"]:hover {
        background-color: #505054;
    }
    
    /* Grupos */
    QGroupBox {
        border: 1px solid #3e3e42;
        border-radius: 5px;
        margin-top: 10px;
        padding-top: 10px;
        font-weight: bold;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px 0 5px;
    }
    
    /* Labels */
    QLabel {
        color: #d4d4d4;
    }
    
    QLabel[title="true"] {
        font-size: 14pt;
        font-weight: bold;
        color: #0e639c;
    }
    
    /* Inputs */
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
        background-color: #3c3c3c;
        border: 1px solid #3e3e42;
        border-radius: 3px;
        padding: 5px;
        color: #d4d4d4;
    }
    
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
        border: 1px solid #0e639c;
    }
    
    /* Slider */
    QSlider::groove:horizontal {
        border: 1px solid #3e3e42;
        height: 4px;
        background: #3e3e42;
        margin: 2px 0;
        border-radius: 2px;
    }
    
    QSlider::handle:horizontal {
        background: #0e639c;
        border: none;
        width: 12px;
        height: 12px;
        margin: -5px 0;
        border-radius: 6px;
    }
    
    /* Progress Bar */
    QProgressBar {
        border: 1px solid #3e3e42;
        border-radius: 3px;
        text-align: center;
        background-color: #3c3c3c;
    }
    
    QProgressBar::chunk {
        background-color: #0e639c;
        border-radius: 2px;
    }
    
    /* Tabs */
    QTabWidget::pane {
        border: 1px solid #3e3e42;
        border-radius: 4px;
        background-color: #252526;
    }
    
    QTabBar::tab {
        background-color: #2d2d30;
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    
    QTabBar::tab:selected {
        background-color: #0e639c;
        color: white;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: #3e3e42;
    }
    
    /* Scroll bars */
    QScrollBar:vertical {
        background-color: #252526;
        width: 12px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical {
        background-color: #3e3e42;
        border-radius: 6px;
        min-height: 20px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #505054;
    }
    
    /* Menu bar */
    QMenuBar {
        background-color: #2d2d30;
        border-bottom: 1px solid #3e3e42;
    }
    
    QMenuBar::item:selected {
        background-color: #0e639c;
    }
    
    QMenu {
        background-color: #2d2d30;
        border: 1px solid #3e3e42;
    }
    
    QMenu::item:selected {
        background-color: #0e639c;
    }
    
    /* Status bar */
    QStatusBar {
        background-color: #007acc;
        color: white;
    }
    
    /* Mensagens de erro */
    QLabel[error="true"] {
        color: #f48771;
    }
    
    /* Mensagens de sucesso */
    QLabel[success="true"] {
        color: #6a9955;
    }
    """
    
    app.setStyleSheet(style)
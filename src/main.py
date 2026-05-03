"""Ponto de entrada principal do aplicativo"""

import sys
import logging
from pathlib import Path

# Configura logging antes de tudo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cnc_pro.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def setup_environment():
    """Configura o ambiente antes de iniciar o app"""
    # Cria diretórios necessários
    dirs = ['images', 'output', 'logs']
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    # Configura Qt para high DPI
    import os
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'


def main():
    """Função principal"""
    try:
        setup_environment()
        
        from PySide6.QtWidgets import QApplication
        from src.gui.main_window import MainWindow
        
        app = QApplication(sys.argv)
        app.setApplicationName("CNC Pro")
        app.setOrganizationName("CNC Pro")
        
        # Carrega estilo
        from src.gui.resources.styles import apply_style
        apply_style(app)
        
        # Cria e mostra janela principal
        window = MainWindow()
        window.show()
        
        logger.info("Aplicação iniciada com sucesso")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Erro ao iniciar aplicação: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
    
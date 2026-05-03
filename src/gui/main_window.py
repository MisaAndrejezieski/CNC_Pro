"""Janela principal do CNC Pro - Versão Simplificada"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QStatusBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from src.core.gerador import GeradorGCode

logger = logging.getLogger(__name__)


class GeracaoThread(QThread):
    """Thread para gerar G-code"""
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, gerador, imagem_path, dimensoes, profundidade):
        super().__init__()
        self.gerador = gerador
        self.imagem_path = imagem_path
        self.dimensoes = dimensoes
        self.profundidade = profundidade
    
    def run(self):
        try:
            gcode = self.gerador.gerar(
                self.imagem_path,
                self.dimensoes,
                self.profundidade
            )
            if gcode:
                self.finished.emit(gcode)
            else:
                self.error.emit("Erro ao gerar G-code")
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Janela principal"""
    
    def __init__(self):
        super().__init__()
        self.gerador = None
        self.current_image = None
        self.gcode_atual = None
        
        self.setWindowTitle("CNC Pro - Gerador de G-code")
        self.setMinimumSize(900, 600)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1 - Arquivo
        tab1 = QWidget()
        layout1 = QVBoxLayout(tab1)
        
        self.image_label = QLabel("Clique ou arraste uma imagem aqui")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(150)
        self.image_label.setStyleSheet("border: 2px dashed gray; padding: 20px;")
        self.image_label.mousePressEvent = self._selecionar_imagem
        layout1.addWidget(self.image_label)
        
        tabs.addTab(tab1, "Imagem")
        
        # Tab 2 - Configurações
        tab2 = QWidget()
        layout2 = QFormLayout(tab2)
        
        self.largura_spin = QDoubleSpinBox()
        self.largura_spin.setRange(1, 500)
        self.largura_spin.setValue(100)
        self.largura_spin.setSuffix(" mm")
        layout2.addRow("Largura:", self.largura_spin)
        
        self.altura_spin = QDoubleSpinBox()
        self.altura_spin.setRange(1, 500)
        self.altura_spin.setValue(100)
        self.altura_spin.setSuffix(" mm")
        layout2.addRow("Altura:", self.altura_spin)
        
        self.profundidade_spin = QDoubleSpinBox()
        self.profundidade_spin.setRange(0.1, 20)
        self.profundidade_spin.setValue(3)
        self.profundidade_spin.setSuffix(" mm")
        layout2.addRow("Profundidade:", self.profundidade_spin)
        
        self.resolucao_spin = QDoubleSpinBox()
        self.resolucao_spin.setRange(1, 50)
        self.resolucao_spin.setValue(10)
        self.resolucao_spin.setSuffix(" passos/mm")
        layout2.addRow("Resolução:", self.resolucao_spin)
        
        self.limiar_spin = QSpinBox()
        self.limiar_spin.setRange(0, 255)
        self.limiar_spin.setValue(128)
        layout2.addRow("Limiar:", self.limiar_spin)
        
        tabs.addTab(tab2, "Configurações")
        
        # Tab 3 - Visualização
        tab3 = QWidget()
        layout3 = QVBoxLayout(tab3)
        
        self.preview_label = QLabel("Pré-visualização")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("background-color: #2d2d30;")
        layout3.addWidget(self.preview_label)
        
        tabs.addTab(tab3, "Visualização")
        
        # Botão Gerar
        self.gerar_btn = QPushButton("GERAR G-CODE")
        self.gerar_btn.setMinimumHeight(40)
        self.gerar_btn.clicked.connect(self._gerar_gcode)
        layout.addWidget(self.gerar_btn)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Botão Salvar
        self.salvar_btn = QPushButton("Salvar G-code")
        self.salvar_btn.setEnabled(False)
        self.salvar_btn.clicked.connect(self._salvar_gcode)
        layout.addWidget(self.salvar_btn)
        
        # Status
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Pronto")
        
        # Drag & drop
        self.setAcceptDrops(True)
    
    def _selecionar_imagem(self, event):
        """Seleciona imagem"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Imagem", "",
            "Imagens (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self._carregar_imagem(file_path)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
    
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self._carregar_imagem(path)
    
    def _carregar_imagem(self, path):
        """Carrega imagem"""
        try:
            self.current_image = path
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.image_label.setText(Path(path).name)
            self.statusBar.showMessage(f"Carregado: {Path(path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não carregou: {e}")
    
    def _gerar_gcode(self):
        """Gera G-code"""
        if not self.current_image:
            QMessageBox.warning(self, "Aviso", "Selecione uma imagem")
            return
        
        config = {
            'gerador': {
                'passos_por_mm': self.resolucao_spin.value(),
                'profundidade_max_corte': 0.5,
                'altura_seguranca_z': 5.0,
                'velocidade_corte': 800,
                'velocidade_rapida': 3500,
                'limiar_preto_branco': self.limiar_spin.value(),
                'diametro_ferramenta': 0.4
            }
        }
        
        self.gerador = GeradorGCode(config)
        
        dimensoes = (self.largura_spin.value(), self.altura_spin.value())
        profundidade = -self.profundidade_spin.value()
        
        self.thread = GeracaoThread(self.gerador, self.current_image, dimensoes, profundidade)
        self.thread.finished.connect(self._geracao_concluida)
        self.thread.error.connect(self._geracao_erro)
        
        self.gerar_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.statusBar.showMessage("Gerando...")
        
        self.thread.start()
    
    def _geracao_concluida(self, gcode):
        self.gcode_atual = gcode
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.salvar_btn.setEnabled(True)
        self.statusBar.showMessage(f"Gerado! {len(gcode)} linhas")
        QMessageBox.information(self, "Sucesso", f"G-code gerado!\n{len(gcode)} linhas")
    
    def _geracao_erro(self, erro):
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.statusBar.showMessage("Erro!")
        QMessageBox.critical(self, "Erro", f"Falha: {erro}")
    
    def _salvar_gcode(self):
        if not self.gcode_atual:
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Salvar G-code", "output/", "G-code (*.nc)")
        if path:
            if self.gerador.salvar(self.gcode_atual, path):
                QMessageBox.information(self, "Sucesso", f"Salvo: {path}")
                self.statusBar.showMessage(f"Salvo: {Path(path).name}")
            else:
                QMessageBox.warning(self, "Erro", "Não salvou")
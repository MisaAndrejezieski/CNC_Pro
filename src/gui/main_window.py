"""Janela principal do CNC Pro - Versão Corrigida"""

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
    QStatusBar
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

# Importa o gerador
from src.core.gerador import GeradorGCode

logger = logging.getLogger(__name__)


class GeracaoThread(QThread):
    """Thread para gerar G-code sem travar a UI"""
    progress = Signal(int)
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
    """Janela principal do CNC Pro"""
    
    def __init__(self):
        super().__init__()
        self.gerador = None
        self.current_image = None
        self.gcode_atual = None
        
        self.setWindowTitle("CNC Pro - Gerador de G-code Profissional")
        self.setMinimumSize(1000, 700)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Arquivo e imagem
        tab_arquivo = self._criar_tab_arquivo()
        tabs.addTab(tab_arquivo, "📁 Arquivo")
        
        # Tab 2: Configurações
        tab_config = self._criar_tab_config()
        tabs.addTab(tab_config, "⚙️ Configurações")
        
        # Tab 3: Visualização
        tab_viz = self._criar_tab_visualizacao()
        tabs.addTab(tab_viz, "🎨 Visualização")
        
        # Botão gerar
        self.gerar_btn = QPushButton("🚀 GERAR G-CODE")
        self.gerar_btn.setMinimumHeight(50)
        self.gerar_btn.clicked.connect(self._gerar_gcode)
        layout.addWidget(self.gerar_btn)
        
        # Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("Pronto")
        layout.addWidget(self.status_label)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Pronto - Aguardando imagem")
        
        # Drag & drop
        self.setAcceptDrops(True)
    
    def _criar_tab_arquivo(self):
        """Cria tab de arquivo"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Área de drop
        self.image_label = QLabel(
            "📸 ARRASTE UMA IMAGEM AQUI\n\n"
            "ou clique para selecionar\n\n"
            "Formatos suportados:\n"
            "PNG, JPG, JPEG, BMP"
        )
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d30;
                border: 2px dashed #0e639c;
                border-radius: 10px;
                padding: 20px;
                color: #888888;
                font-size: 12pt;
            }
            QLabel:hover {
                background-color: #3e3e42;
                border-color: #1177bb;
            }
        """)
        self.image_label.mousePressEvent = self._selecionar_imagem
        layout.addWidget(self.image_label)
        
        # Info da imagem
        group_info = QGroupBox("Informações da Imagem")
        info_layout = QFormLayout(group_info)
        
        self.info_nome = QLabel("-")
        self.info_tamanho = QLabel("-")
        self.info_resolucao = QLabel("-")
        
        info_layout.addRow("Arquivo:", self.info_nome)
        info_layout.addRow("Dimensões (px):", self.info_tamanho)
        info_layout.addRow("Resolução:", self.info_resolucao)
        
        layout.addWidget(group_info)
        
        return widget
    
    def _criar_tab_config(self):
        """Cria tab de configurações"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        # Dimensões
        self.largura_spin = QDoubleSpinBox()
        self.largura_spin.setRange(1, 1000)
        self.largura_spin.setValue(100)
        self.largura_spin.setSuffix(" mm")
        layout.addRow("Largura física:", self.largura_spin)
        
        self.altura_spin = QDoubleSpinBox()
        self.altura_spin.setRange(1, 1000)
        self.altura_spin.setValue(100)
        self.altura_spin.setSuffix(" mm")
        layout.addRow("Altura física:", self.altura_spin)
        
        # Corte
        self.profundidade_spin = QDoubleSpinBox()
        self.profundidade_spin.setRange(0.1, 50)
        self.profundidade_spin.setValue(3)
        self.profundidade_spin.setSuffix(" mm")
        layout.addRow("Profundidade total:", self.profundidade_spin)
        
        self.passo_corte_spin = QDoubleSpinBox()
        self.passo_corte_spin.setRange(0.1, 5)
        self.passo_corte_spin.setValue(0.5)
        self.passo_corte_spin.setSuffix(" mm")
        layout.addRow("Profundidade por passe:", self.passo_corte_spin)
        
        # Velocidades
        self.vel_corte_spin = QDoubleSpinBox()
        self.vel_corte_spin.setRange(10, 5000)
        self.vel_corte_spin.setValue(800)
        self.vel_corte_spin.setSuffix(" mm/min")
        layout.addRow("Velocidade de corte:", self.vel_corte_spin)
        
        self.vel_rapida_spin = QDoubleSpinBox()
        self.vel_rapida_spin.setRange(10, 10000)
        self.vel_rapida_spin.setValue(3500)
        self.vel_rapida_spin.setSuffix(" mm/min")
        layout.addRow("Velocidade rápida:", self.vel_rapida_spin)
        
        # Resolução
        self.resolucao_spin = QDoubleSpinBox()
        self.resolucao_spin.setRange(1, 100)
        self.resolucao_spin.setValue(10)
        self.resolucao_spin.setSuffix(" passos/mm")
        self.resolucao_spin.setToolTip("Maior resolução = mais detalhes, porém arquivo maior")
        layout.addRow("Resolução:", self.resolucao_spin)
        
        # Limiar
        self.limiar_spin = QSpinBox()
        self.limiar_spin.setRange(0, 255)
        self.limiar_spin.setValue(128)
        layout.addRow("Limiar preto/branco:", self.limiar_spin)
        
        # Ferramenta
        self.diametro_spin = QDoubleSpinBox()
        self.diametro_spin.setRange(0.1, 10)
        self.diametro_spin.setValue(0.4)
        self.diametro_spin.setSuffix(" mm")
        layout.addRow("Diâmetro da ferramenta:", self.diametro_spin)
        
        return widget
    
    def _criar_tab_visualizacao(self):
        """Cria tab de visualização"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.preview_label = QLabel("Pré-visualização da imagem")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(400)
        self.preview_label.setStyleSheet("background-color: #2d2d30; border-radius: 5px;")
        layout.addWidget(self.preview_label)
        
        # Botões de ação
        btn_layout = QHBoxLayout()
        
        self.salvar_btn = QPushButton("💾 Salvar G-code")
        self.salvar_btn.setEnabled(False)
        self.salvar_btn.clicked.connect(self._salvar_gcode)
        btn_layout.addWidget(self.salvar_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def _selecionar_imagem(self, event):
        """Seleciona imagem via diálogo"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem",
            str(Path("images").absolute()),
            "Imagens (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self._carregar_imagem(file_path)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Evento de drag enter"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """Evento de drop"""
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self._carregar_imagem(path)
    
    def _carregar_imagem(self, path: str):
        """Carrega e exibe imagem"""
        try:
            from PIL import Image
            
            self.current_image = path
            
            # Carrega com PIL para obter dimensões
            img = Image.open(path)
            width, height = img.size
            
            # Exibe preview
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(500, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            
            # Atualiza informações
            nome = Path(path).name
            self.image_label.setText(f"✅ {nome}")
            self.info_nome.setText(nome)
            self.info_tamanho.setText(f"{width} x {height} px")
            self.info_resolucao.setText(f"{img.info.get('dpi', (72,72))[0]} dpi")
            
            self.statusBar.showMessage(f"Imagem carregada: {nome}")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível carregar a imagem:\n{e}")
    
    def _gerar_gcode(self):
        """Gera G-code"""
        if not self.current_image:
            QMessageBox.warning(self, "Aviso", "Selecione ou arraste uma imagem primeiro")
            return
        
        # Configura o gerador
        config = {
            'gerador': {
                'passos_por_mm': self.resolucao_spin.value(),
                'profundidade_max_corte': self.passo_corte_spin.value(),
                'altura_seguranca_z': 5.0,
                'velocidade_corte': self.vel_corte_spin.value(),
                'velocidade_rapida': self.vel_rapida_spin.value(),
                'limiar_preto_branco': self.limiar_spin.value(),
                'diametro_ferramenta': self.diametro_spin.value(),
                'sobreposicao': 0.4,
                'suavizar_imagem': False
            }
        }
        
        self.gerador = GeradorGCode(config)
        
        # Prepara thread
        dimensoes = (self.largura_spin.value(), self.altura_spin.value())
        profundidade = -self.profundidade_spin.value()
        
        self.thread = GeracaoThread(
            self.gerador,
            self.current_image,
            dimensoes,
            profundidade
        )
        self.thread.finished.connect(self._geracao_concluida)
        self.thread.error.connect(self._geracao_erro)
        
        # Desabilita botão e mostra progresso
        self.gerar_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        self.status_label.setText("🔄 Gerando G-code...")
        self.statusBar.showMessage("Gerando G-code, aguarde...")
        
        self.thread.start()
    
    def _geracao_concluida(self, gcode):
        """Geração concluída com sucesso"""
        self.gcode_atual = gcode
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.salvar_btn.setEnabled(True)
        self.status_label.setText(f"✅ G-code gerado! {len(gcode)} linhas")
        self.statusBar.showMessage(f"G-code gerado: {len(gcode)} linhas")
        
        QMessageBox.information(
            self,
            "Sucesso",
            f"✨ G-code gerado com sucesso!\n\n"
            f"📊 Total de linhas: {len(gcode)}\n"
            f"🎯 Clique em 'Salvar G-code' para exportar."
        )
    
    def _geracao_erro(self, erro):
        """Erro na geração"""
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText("❌ Erro na geração")
        self.statusBar.showMessage("Erro ao gerar G-code")
        
        QMessageBox.critical(
            self,
            "Erro",
            f"❌ Falha ao gerar G-code:\n\n{erro}"
        )
    
    def _salvar_gcode(self):
        """Salva G-code em arquivo"""
        if not self.gcode_atual:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar G-code",
            str(Path("output").absolute()),
            "Arquivos G-code (*.nc);;Todos os arquivos (*.*)"
        )
        
        if path:
            if self.gerador.salvar(self.gcode_atual, path):
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"✅ G-code salvo com sucesso!\n\n📁 {path}"
                )
                self.statusBar.showMessage(f"Salvo: {Path(path).name}")
            else:
                QMessageBox.warning(self, "Erro", "❌ Erro ao salvar o arquivo")
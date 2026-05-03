"""Janela principal do aplicativo"""

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QComboBox, QCheckBox,
    QStatusBar, QSplitter, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from src.core.gerador import GeradorGCode
from src.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class GeracaoThread(QThread):
    """Thread para geração de G-code (não travar a interface)"""
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(object)
    error = Signal(str)
    
    def __init__(self, gerador: GeradorGCode, imagem_path: str,
                 dimensoes: tuple, profundidade: float):
        super().__init__()
        self.gerador = gerador
        self.imagem_path = imagem_path
        self.dimensoes = dimensoes
        self.profundidade = profundidade
    
    def run(self):
        try:
            self.log.emit("Processando imagem...")
            self.progress.emit(25)
            
            gcode = self.gerador.gerar(
                self.imagem_path,
                self.dimensoes,
                self.profundidade
            )
            
            self.progress.emit(75)
            self.log.emit("Finalizando...")
            
            if gcode:
                self.finished.emit(gcode)
            else:
                self.error.emit("Erro ao gerar G-code")
            
            self.progress.emit(100)
            
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Janela principal do CNC Pro"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.gerador: Optional[GeradorGCode] = None
        self.current_image_path: Optional[str] = None
        self.gcode_atual: Optional[list] = None
        
        self.setWindowTitle("CNC Pro - Gerador de G-code Profissional")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Layout principal com splitter
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Painel esquerdo (controles)
        left_panel = self._criar_painel_controle()
        main_splitter.addWidget(left_panel)
        
        # Painel direito (visualização)
        right_panel = self._criar_painel_visualizacao()
        main_splitter.addWidget(right_panel)
        
        # Define proporções
        main_splitter.setSizes([400, 800])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto")
        
        # Configura drag & drop
        self.setAcceptDrops(True)
        
        # Timer para animação de carregamento
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self._update_loading_animation)
        self.loading_dots = 0
        
        # Carrega configurações
        self._carregar_configuracoes()
        
        # Inicializa gerador
        self._reinicializar_gerador()
    
    def _criar_painel_controle(self) -> QWidget:
        """Cria painel com controles"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabs para organização
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab: Arquivo
        tab_arquivo = self._criar_tab_arquivo()
        tabs.addTab(tab_arquivo, "📁 Arquivo")
        
        # Tab: Dimensões
        tab_dimensoes = self._criar_tab_dimensoes()
        tabs.addTab(tab_dimensoes, "📏 Dimensões")
        
        # Tab: Corte
        tab_corte = self._criar_tab_corte()
        tabs.addTab(tab_corte, "⚙️ Corte")
        
        # Tab: Avançado
        tab_avancado = self._criar_tab_avancado()
        tabs.addTab(tab_avancado, "🔧 Avançado")
        
        # Botão gerar
        self.gerar_btn = QPushButton("🚀 GERAR G-CODE")
        self.gerar_btn.setMinimumHeight(50)
        self.gerar_btn.clicked.connect(self._gerar_gcode)
        layout.addWidget(self.gerar_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Log de status
        self.log_label = QLabel()
        self.log_label.setWordWrap(True)
        self.log_label.setStyleSheet("background-color: #1e1e1e; padding: 5px; border-radius: 3px;")
        self.log_label.setMaximumHeight(80)
        layout.addWidget(self.log_label)
        
        return widget
    
    def _criar_tab_arquivo(self) -> QWidget:
        """Tab de seleção de arquivo"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Seleção de imagem
        group = QGroupBox("Imagem de Entrada")
        group_layout = QVBoxLayout(group)
        
        self.image_label = QLabel("Arraste uma imagem aqui\nou clique para selecionar")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(200)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d30;
                border: 2px dashed #3e3e42;
                border-radius: 5px;
                color: #6e6e6e;
            }
        """)
        self.image_label.mousePressEvent = self._selecionar_imagem
        group_layout.addWidget(self.image_label)
        
        layout.addWidget(group)
        
        # Informações da imagem
        group_info = QGroupBox("Informações")
        info_layout = QFormLayout(group_info)
        
        self.info_tamanho = QLabel("-")
        self.info_resolucao = QLabel("-")
        self.info_canais = QLabel("-")
        
        info_layout.addRow("Tamanho:", self.info_tamanho)
        info_layout.addRow("Resolução:", self.info_resolucao)
        info_layout.addRow("Canais:", self.info_canais)
        
        layout.addWidget(group_info)
        
        # Histórico
        group_historico = QGroupBox("Últimos Arquivos")
        hist_layout = QVBoxLayout(group_historico)
        self.historico_list = QLabel("Nenhum arquivo recente")
        self.historico_list.setWordWrap(True)
        hist_layout.addWidget(self.historico_list)
        layout.addWidget(group_historico)
        
        layout.addStretch()
        return widget
    
    def _criar_tab_dimensoes(self) -> QWidget:
        """Tab de configuração de dimensões"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        self.largura_spin = QDoubleSpinBox()
        self.largura_spin.setRange(0.1, 1000)
        self.largura_spin.setValue(100)
        self.largura_spin.setSuffix(" mm")
        layout.addRow("Largura:", self.largura_spin)
        
        self.altura_spin = QDoubleSpinBox()
        self.altura_spin.setRange(0.1, 1000)
        self.altura_spin.setValue(100)
        self.altura_spin.setSuffix(" mm")
        layout.addRow("Altura:", self.altura_spin)
        
        self.manter_proporcao = QCheckBox("Manter proporção da imagem")
        self.manter_proporcao.setChecked(True)
        layout.addRow("", self.manter_proporcao)
        
        # Resolução
        self.resolucao_spin = QDoubleSpinBox()
        self.resolucao_spin.setRange(1, 100)
        self.resolucao_spin.setValue(10)
        self.resolucao_spin.setSuffix(" passos/mm")
        self.resolucao_spin.setToolTip("Quanto maior, mais detalhes mas arquivo maior")
        layout.addRow("Resolução:", self.resolucao_spin)
        
        # Linkar largura/altura
        self.largura_spin.valueChanged.connect(self._on_largura_changed)
        self.altura_spin.valueChanged.connect(self._on_altura_changed)
        
        layout.addRow(QLabel())
        layout.addRow(QLabel("💡 Dica: Maior resolução = mais detalhes"))
        
        return widget
    
    def _criar_tab_corte(self) -> QWidget:
        """Tab de configurações de corte"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        self.profundidade_spin = QDoubleSpinBox()
        self.profundidade_spin.setRange(0.1, 50)
        self.profundidade_spin.setValue(3.0)
        self.profundidade_spin.setSuffix(" mm")
        self.profundidade_spin.setToolTip("Profundidade total de corte")
        layout.addRow("Profundidade total:", self.profundidade_spin)
        
        self.passo_corte_spin = QDoubleSpinBox()
        self.passo_corte_spin.setRange(0.1, 5)
        self.passo_corte_spin.setValue(0.5)
        self.passo_corte_spin.setSuffix(" mm")
        self.passo_corte_spin.setToolTip("Profundidade máxima por passe")
        layout.addRow("Profundidade/passe:", self.passo_corte_spin)
        
        self.velocidade_corte_spin = QDoubleSpinBox()
        self.velocidade_corte_spin.setRange(10, 5000)
        self.velocidade_corte_spin.setValue(800)
        self.velocidade_corte_spin.setSuffix(" mm/min")
        layout.addRow("Velocidade de corte:", self.velocidade_corte_spin)
        
        self.velocidade_rapida_spin = QDoubleSpinBox()
        self.velocidade_rapida_spin.setRange(10, 10000)
        self.velocidade_rapida_spin.setValue(3500)
        self.velocidade_rapida_spin.setSuffix(" mm/min")
        layout.addRow("Velocidade rápida:", self.velocidade_rapida_spin)
        
        self.estrategia_combo = QComboBox()
        self.estrategia_combo.addItems(["Zig-Zag", "Linha Única", "Espiral", "Otimizado"])
        layout.addRow("Estratégia:", self.estrategia_combo)
        
        return widget
    
    def _criar_tab_avancado(self) -> QWidget:
        """Tab de configurações avançadas"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        
        self.limiar_spin = QSpinBox()
        self.limiar_spin.setRange(0, 255)
        self.limiar_spin.setValue(128)
        layout.addRow("Limiar preto/branco:", self.limiar_spin)
        
        self.diametro_tool = QDoubleSpinBox()
        self.diametro_tool.setRange(0.1, 10)
        self.diametro_tool.setValue(0.4)
        self.diametro_tool.setSuffix(" mm")
        layout.addRow("Diâmetro da ferramenta:", self.diametro_tool)
        
        self.sobreposicao_spin = QDoubleSpinBox()
        self.sobreposicao_spin.setRange(0, 0.9)
        self.sobreposicao_spin.setValue(0.4)
        self.sobreposicao_spin.setSingleStep(0.1)
        layout.addRow("Sobreposição:", self.sobreposicao_spin)
        
        self.altura_seguranca = QDoubleSpinBox()
        self.altura_seguranca.setRange(1, 50)
        self.altura_seguranca.setValue(5)
        self.altura_seguranca.setSuffix(" mm")
        layout.addRow("Altura de segurança:", self.altura_seguranca)
        
        self.suavizar_check = QCheckBox("Suavizar imagem")
        layout.addRow("", self.suavizar_check)
        
        return widget
    
    def _criar_painel_visualizacao(self) -> QWidget:
        """Cria painel de visualização"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab: Preview da imagem
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        self.preview_label = QLabel("Pré-visualização da imagem")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("background-color: #2d2d30; border-radius: 5px;")
        preview_layout.addWidget(self.preview_label)
        tabs.addTab(preview_tab, "🖼️ Pré-visualização")
        
        # Tab: Visualização 3D
        # TODO: Implementar visualização 3D
        viz3d_tab = QWidget()
        viz3d_layout = QVBoxLayout(viz3d_tab)
        viz3d_label = QLabel("Visualização 3D (em desenvolvimento)")
        viz3d_label.setAlignment(Qt.AlignCenter)
        viz3d_layout.addWidget(viz3d_label)
        tabs.addTab(viz3d_tab, "🎨 3D Preview")
        
        # Botões de ação
        btn_layout = QHBoxLayout()
        
        self.salvar_btn = QPushButton("💾 Salvar G-code")
        self.salvar_btn.setEnabled(False)
        self.salvar_btn.clicked.connect(self._salvar_gcode)
        btn_layout.addWidget(self.salvar_btn)
        
        self.editar_btn = QPushButton("✏️ Editar")
        self.editar_btn.setEnabled(False)
        btn_layout.addWidget(self.editar_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def _selecionar_imagem(self, event):
        """Abre diálogo para selecionar imagem"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem",
            str(Path("images").absolute()),
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tiff)"
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
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self._carregar_imagem(file_path)
    
    def _carregar_imagem(self, path: str):
        """Carrega e exibe imagem"""
        try:
            from PIL import Image
            import numpy as np
            
            self.current_image_path = path
            
            # Carrega com PIL
            img = Image.open(path)
            
            # Exibe preview
            pixmap = QPixmap(path)
            scaled = pixmap.scaled(
                400, 300,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
            self.image_label.setText(path.split('/')[-1])
            
            # Atualiza info
            self.info_tamanho.setText(f"{img.width} x {img.height} px")
            self.info_resolucao.setText(f"{img.info.get('dpi', 'N/A')} dpi")
            self.info_canais.setText(img.mode)
            
            # Atualiza dimensões automaticamente se manter proporção
            if self.manter_proporcao.isChecked():
                proporcao = img.width / img.height
                self.altura_spin.blockSignals(True)
                self.altura_spin.setValue(self.largura_spin.value() / proporcao)
                self.altura_spin.blockSignals(False)
            
            self.status_bar.showMessage(f"Imagem carregada: {path}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar imagem: {e}")
            QMessageBox.warning(self, "Erro", f"Não foi possível carregar a imagem:\n{e}")
    
    def _on_largura_changed(self):
        """Quando largura muda, ajusta altura proporcionalmente"""
        if self.manter_proporcao.isChecked() and self.current_image_path:
            from PIL import Image
            img = Image.open(self.current_image_path)
            proporcao = img.width / img.height
            self.altura_spin.blockSignals(True)
            self.altura_spin.setValue(self.largura_spin.value() / proporcao)
            self.altura_spin.blockSignals(False)
    
    def _on_altura_changed(self):
        """Quando altura muda, ajusta largura proporcionalmente"""
        if self.manter_proporcao.isChecked() and self.current_image_path:
            from PIL import Image
            img = Image.open(self.current_image_path)
            proporcao = img.width / img.height
            self.largura_spin.blockSignals(True)
            self.largura_spin.setValue(self.altura_spin.value() * proporcao)
            self.largura_spin.blockSignals(False)
    
    def _carregar_configuracoes(self):
        """Carrega configurações salvas"""
        config = self.config_manager.load()
        
        # Aplica valores
        self.largura_spin.setValue(config.get('dimensoes', {}).get('largura', 100))
        self.altura_spin.setValue(config.get('dimensoes', {}).get('altura', 100))
        self.resolucao_spin.setValue(config.get('resolucao', 10))
        self.profundidade_spin.setValue(config.get('profundidade', 3))
        self.passo_corte_spin.setValue(config.get('passo_corte', 0.5))
        self.velocidade_corte_spin.setValue(config.get('velocidade_corte', 800))
        self.velocidade_rapida_spin.setValue(config.get('velocidade_rapida', 3500))
        self.limiar_spin.setValue(config.get('limiar', 128))
    
    def _salvar_configuracoes(self):
        """Salva configurações atuais"""
        config = {
            'dimensoes': {
                'largura': self.largura_spin.value(),
                'altura': self.altura_spin.value()
            },
            'resolucao': self.resolucao_spin.value(),
            'profundidade': self.profundidade_spin.value(),
            'passo_corte': self.passo_corte_spin.value(),
            'velocidade_corte': self.velocidade_corte_spin.value(),
            'velocidade_rapida': self.velocidade_rapida_spin.value(),
            'limiar': self.limiar_spin.value(),
        }
        self.config_manager.save(config)
    
    def _reinicializar_gerador(self):
        """Reinicializa o gerador com configurações atuais"""
        config = {
            'gerador': {
                'passos_por_mm': self.resolucao_spin.value(),
                'profundidade_max_corte': self.passo_corte_spin.value(),
                'altura_seguranca_z': self.altura_seguranca.value(),
                'velocidade_corte': self.velocidade_corte_spin.value(),
                'velocidade_rapida': self.velocidade_rapida_spin.value(),
                'limiar_preto_branco': self.limiar_spin.value(),
                'diametro_ferramenta': self.diametro_tool.value(),
                'sobreposicao': self.sobreposicao_spin.value(),
                'estrategia_varredura': self.estrategia_combo.currentText().lower().replace('-', '_'),
                'suavizar_imagem': self.suavizar_check.isChecked()
            }
        }
        self.gerador = GeradorGCode(config)
    
    def _gerar_gcode(self):
        """Inicia geração de G-code"""
        if not self.current_image_path:
            QMessageBox.warning(self, "Aviso", "Selecione uma imagem primeiro")
            return
        
        # Salva configurações
        self._salvar_configuracoes()
        self._reinicializar_gerador()
        
        # Prepara thread
        dimensoes = (self.largura_spin.value(), self.altura_spin.value())
        profundidade = -self.profundidade_spin.value()
        
        self.geracao_thread = GeracaoThread(
            self.gerador,
            self.current_image_path,
            dimensoes,
            profundidade
        )
        
        # Conecta sinais
        self.geracao_thread.progress.connect(self._atualizar_progresso)
        self.geracao_thread.log.connect(self._atualizar_log)
        self.geracao_thread.finished.connect(self._geracao_concluida)
        self.geracao_thread.error.connect(self._geracao_erro)
        
        # Desabilita botão durante geração
        self.gerar_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # Inicia
        self.geracao_thread.start()
        
        # Inicia animação de loading
        self.loading_timer.start(500)
    
    def _atualizar_progresso(self, valor: int):
        """Atualiza barra de progresso"""
        self.progress_bar.setValue(valor)
    
    def _atualizar_log(self, mensagem: str):
        """Atualiza log de status"""
        self.log_label.setText(mensagem)
        self.status_bar.showMessage(mensagem)
    
    def _update_loading_animation(self):
        """Atualiza animação de carregamento"""
        self.loading_dots = (self.loading_dots + 1) % 4
        dots = "." * self.loading_dots
        self.log_label.setText(f"Processando{dots.ljust(3)}")
    
    def _geracao_concluida(self, gcode: list):
        """Quando geração termina com sucesso"""
        self.loading_timer.stop()
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.gcode_atual = gcode
        self.salvar_btn.setEnabled(True)
        self.editar_btn.setEnabled(True)
        
        QMessageBox.information(
            self,
            "Sucesso",
            f"G-code gerado com sucesso!\nTotal de {len(gcode)} linhas."
        )
        self.status_bar.showMessage("G-code gerado com sucesso")
    
    def _geracao_erro(self, erro: str):
        """Quando ocorre erro na geração"""
        self.loading_timer.stop()
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        
        QMessageBox.critical(self, "Erro", f"Erro ao gerar G-code:\n{erro}")
        self.status_bar.showMessage("Erro na geração")
    
    def _salvar_gcode(self):
        """Salva G-code em arquivo"""
        if not self.gcode_atual:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar G-code",
            str(Path("output").absolute()),
            "Arquivos G-code (*.nc *.gcode);;Todos os arquivos (*.*)"
        )
        
        if file_path:
            if self.gerador.salvar(self.gcode_atual, file_path):
                QMessageBox.information(self, "Sucesso", f"G-code salvo em:\n{file_path}")
                self.status_bar.showMessage(f"Salvo: {file_path}")
            else:
                QMessageBox.warning(self, "Erro", "Erro ao salvar arquivo")
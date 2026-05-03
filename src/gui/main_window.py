"""Janela principal do CNC Pro - Com Visualizador 3D"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox,
    QProgressBar, QTabWidget, QGroupBox, QFormLayout,
    QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox,
    QStatusBar, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QFont

from src.core.gerador import GeradorGCode
from src.gui.visualizador_3d import Visualizador3D

logger = logging.getLogger(__name__)


class GeracaoThread(QThread):
    """Thread para gerar G-code sem travar a interface"""
    progress = Signal(int)
    log = Signal(str)
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
            self.log.emit("Processando imagem...")
            gcode = self.gerador.gerar(
                self.imagem_path,
                self.dimensoes,
                self.profundidade
            )
            if gcode:
                self.log.emit(f"Gerado: {len(gcode)} linhas")
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
        self.dimensoes_atuais = (100, 100)
        
        self.setWindowTitle("CNC Pro - Gerador de G-code Profissional")
        self.setMinimumSize(1200, 700)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Splitter principal
        main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(main_splitter)
        
        # Painel esquerdo (controles)
        left_panel = self._criar_painel_controle()
        main_splitter.addWidget(left_panel)
        
        # Painel direito (visualização)
        right_panel = self._criar_painel_visualizacao()
        main_splitter.addWidget(right_panel)
        
        # Proporções
        main_splitter.setSizes([400, 800])
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("✅ Pronto - Aguardando imagem")
        
        # Drag & drop
        self.setAcceptDrops(True)
    
    def _criar_painel_controle(self) -> QWidget:
        """Cria painel de controles"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabs para organização
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Arquivo
        tab_arquivo = self._criar_tab_arquivo()
        tabs.addTab(tab_arquivo, "📁 Arquivo")
        
        # Tab 2: Dimensões
        tab_dimensoes = self._criar_tab_dimensoes()
        tabs.addTab(tab_dimensoes, "📏 Dimensões")
        
        # Tab 3: Corte
        tab_corte = self._criar_tab_corte()
        tabs.addTab(tab_corte, "⚙️ Corte")
        
        # Tab 4: Avançado
        tab_avancado = self._criar_tab_avancado()
        tabs.addTab(tab_avancado, "🔧 Avançado")
        
        # Botão Gerar
        self.gerar_btn = QPushButton("🚀 GERAR G-CODE")
        self.gerar_btn.setMinimumHeight(50)
        self.gerar_btn.clicked.connect(self._gerar_gcode)
        layout.addWidget(self.gerar_btn)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Pronto")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("background-color: #2d2d30; padding: 5px; border-radius: 3px;")
        self.status_label.setMaximumHeight(60)
        layout.addWidget(self.status_label)
        
        return widget
    
    def _criar_tab_arquivo(self) -> QWidget:
        """Tab de seleção de arquivo"""
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
        
        # Informações da imagem
        group_info = QGroupBox("Informações da Imagem")
        info_layout = QFormLayout(group_info)
        
        self.info_nome = QLabel("-")
        self.info_tamanho = QLabel("-")
        self.info_resolucao = QLabel("-")
        
        info_layout.addRow("Arquivo:", self.info_nome)
        info_layout.addRow("Dimensões (px):", self.info_tamanho)
        info_layout.addRow("Resolução:", self.info_resolucao)
        
        layout.addWidget(group_info)
        
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
        self.largura_spin.valueChanged.connect(self._on_largura_changed)
        layout.addRow("Largura:", self.largura_spin)
        
        self.altura_spin = QDoubleSpinBox()
        self.altura_spin.setRange(0.1, 1000)
        self.altura_spin.setValue(100)
        self.altura_spin.setSuffix(" mm")
        self.altura_spin.valueChanged.connect(self._on_altura_changed)
        layout.addRow("Altura:", self.altura_spin)
        
        self.manter_proporcao = QCheckBox("Manter proporção da imagem")
        self.manter_proporcao.setChecked(True)
        layout.addRow("", self.manter_proporcao)
        
        self.resolucao_spin = QDoubleSpinBox()
        self.resolucao_spin.setRange(1, 100)
        self.resolucao_spin.setValue(10)
        self.resolucao_spin.setSuffix(" passos/mm")
        self.resolucao_spin.setToolTip("Maior resolução = mais detalhes, porém arquivo maior")
        layout.addRow("Resolução:", self.resolucao_spin)
        
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
        layout.addRow("Profundidade total:", self.profundidade_spin)
        
        self.passo_corte_spin = QDoubleSpinBox()
        self.passo_corte_spin.setRange(0.1, 5)
        self.passo_corte_spin.setValue(0.5)
        self.passo_corte_spin.setSuffix(" mm")
        layout.addRow("Profundidade por passe:", self.passo_corte_spin)
        
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
        self.estrategia_combo.addItems(["Zig-Zag", "Linha Única", "Otimizado"])
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
        
        self.altura_seguranca = QDoubleSpinBox()
        self.altura_seguranca.setRange(1, 50)
        self.altura_seguranca.setValue(5)
        self.altura_seguranca.setSuffix(" mm")
        layout.addRow("Altura de segurança:", self.altura_seguranca)
        
        self.suavizar_check = QCheckBox("Suavizar imagem")
        layout.addRow("", self.suavizar_check)
        
        return widget
    
    def _criar_painel_visualizacao(self) -> QWidget:
        """Cria painel de visualização com 3D"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Tabs de visualização
        viz_tabs = QTabWidget()
        layout.addWidget(viz_tabs)
        
        # Tab 1: Preview da imagem
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        self.preview_label = QLabel("Pré-visualização da imagem")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("background-color: #2d2d30; border-radius: 5px;")
        preview_layout.addWidget(self.preview_label)
        
        viz_tabs.addTab(preview_tab, "🖼️ Imagem")
        
        # Tab 2: Visualização 3D
        viz_3d_tab = QWidget()
        viz_3d_layout = QVBoxLayout(viz_3d_tab)
        
        self.visualizador_3d = Visualizador3D()
        viz_3d_layout.addWidget(self.visualizador_3d)
        
        viz_tabs.addTab(viz_3d_tab, "🎨 3D")
        
        # Tab 3: Estatísticas
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        self.stats_label = QLabel("Gere um G-code para ver as estatísticas")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("background-color: #2d2d30; padding: 10px; border-radius: 5px;")
        stats_layout.addWidget(self.stats_label)
        
        viz_tabs.addTab(stats_tab, "📊 Estatísticas")
        
        # Botões
        btn_layout = QHBoxLayout()
        
        self.salvar_btn = QPushButton("💾 Salvar G-code")
        self.salvar_btn.setEnabled(False)
        self.salvar_btn.clicked.connect(self._salvar_gcode)
        btn_layout.addWidget(self.salvar_btn)
        
        self.salvar_viz_btn = QPushButton("📸 Salvar Visualização 3D")
        self.salvar_viz_btn.setEnabled(False)
        self.salvar_viz_btn.clicked.connect(self._salvar_visualizacao)
        btn_layout.addWidget(self.salvar_viz_btn)
        
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
        if event.mimeData().hasUrls():
            event.accept()
    
    def dropEvent(self, event: QDropEvent):
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
            
            dpi = img.info.get('dpi', (72, 72))
            if isinstance(dpi, tuple):
                self.info_resolucao.setText(f"{dpi[0]} x {dpi[1]} dpi")
            else:
                self.info_resolucao.setText(f"{dpi} dpi")
            
            # Atualiza dimensões se manter proporção
            if self.manter_proporcao.isChecked():
                proporcao = width / height
                self.altura_spin.blockSignals(True)
                self.altura_spin.setValue(self.largura_spin.value() / proporcao)
                self.altura_spin.blockSignals(False)
            
            self.statusBar.showMessage(f"✅ Imagem carregada: {nome}")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível carregar a imagem:\n{e}")
    
    def _on_largura_changed(self):
        """Quando largura muda, ajusta altura proporcionalmente"""
        if self.manter_proporcao.isChecked() and self.current_image:
            from PIL import Image
            img = Image.open(self.current_image)
            proporcao = img.width / img.height
            self.altura_spin.blockSignals(True)
            self.altura_spin.setValue(self.largura_spin.value() / proporcao)
            self.altura_spin.blockSignals(False)
    
    def _on_altura_changed(self):
        """Quando altura muda, ajusta largura proporcionalmente"""
        if self.manter_proporcao.isChecked() and self.current_image:
            from PIL import Image
            img = Image.open(self.current_image)
            proporcao = img.width / img.height
            self.largura_spin.blockSignals(True)
            self.largura_spin.setValue(self.altura_spin.value() * proporcao)
            self.largura_spin.blockSignals(False)
    
    def _gerar_gcode(self):
        """Gera G-code"""
        if not self.current_image:
            QMessageBox.warning(self, "Aviso", "Selecione ou arraste uma imagem primeiro")
            return
        
        # Prepara configuração
        config = {
            'gerador': {
                'passos_por_mm': self.resolucao_spin.value(),
                'profundidade_max_corte': self.passo_corte_spin.value(),
                'altura_seguranca_z': self.altura_seguranca.value(),
                'velocidade_corte': self.velocidade_corte_spin.value(),
                'velocidade_rapida': self.velocidade_rapida_spin.value(),
                'limiar_preto_branco': self.limiar_spin.value(),
                'diametro_ferramenta': self.diametro_tool.value(),
                'suavizar_imagem': self.suavizar_check.isChecked()
            }
        }
        
        self.gerador = GeradorGCode(config)
        
        # Inicia thread
        self.dimensoes_atuais = (self.largura_spin.value(), self.altura_spin.value())
        profundidade = -self.profundidade_spin.value()
        
        self.thread = GeracaoThread(
            self.gerador,
            self.current_image,
            self.dimensoes_atuais,
            profundidade
        )
        self.thread.log.connect(self._atualizar_log)
        self.thread.finished.connect(self._geracao_concluida)
        self.thread.error.connect(self._geracao_erro)
        
        # Desabilita botão e mostra progresso
        self.gerar_btn.setEnabled(False)
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("🔄 Processando imagem...")
        self.statusBar.showMessage("Gerando G-code, aguarde...")
        
        self.thread.start()
    
    def _atualizar_log(self, mensagem: str):
        """Atualiza log de status"""
        self.status_label.setText(f"🔄 {mensagem}")
        self.statusBar.showMessage(mensagem)
    
    def _geracao_concluida(self, gcode):
        """Geração concluída com sucesso"""
        self.gcode_atual = gcode
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.salvar_btn.setEnabled(True)
        self.salvar_viz_btn.setEnabled(True)
        
        # Carrega visualização 3D
        self.visualizador_3d.carregar_gcode(gcode, self.dimensoes_atuais)
        
        # Exibe estatísticas
        stats = self.gerador.analisar_gcode(gcode)
        self._exibir_estatisticas(stats)
        
        self.status_label.setText(f"✅ G-code gerado! {len(gcode)} linhas")
        self.statusBar.showMessage(f"G-code gerado: {len(gcode)} linhas")
        
        QMessageBox.information(
            self,
            "Sucesso",
            f"✨ G-code gerado com sucesso!\n\n"
            f"📊 Total de linhas: {len(gcode)}\n"
            f"🎯 Movimentos de corte: {stats['movimentos_corte']}\n"
            f"💨 Movimentos rápidos: {stats['movimentos_rapidos']}\n"
            f"📏 Distância total: {stats['distancia_total']:.1f} mm\n"
            f"🎨 Visualização 3D disponível na aba"
        )
    
    def _exibir_estatisticas(self, stats: dict):
        """Exibe estatísticas na tab"""
        texto = f"""
        📊 ESTATÍSTICAS DO G-CODE
        
        {'=' * 40}
        
        📄 Informações Básicas:
        • Total de linhas: {stats['total_linhas']}
        
        🎯 Movimentos:
        • Movimentos de corte (G1): {stats['movimentos_corte']}
        • Movimentos rápidos (G0): {stats['movimentos_rapidos']}
        
        📏 Distâncias:
        • Distância total percorrida: {stats['distancia_total']:.1f} mm
        
        🔧 Profundidade:
        • Profundidade máxima: {abs(stats['profundidade_maxima']):.2f} mm
        
        {'=' * 40}
        
        💡 Dica: Use a aba "3D" para visualizar a trajetória
        """
        self.stats_label.setText(texto)
    
    def _geracao_erro(self, erro):
        """Erro na geração"""
        self.gerar_btn.setEnabled(True)
        self.progress_bar.hide()
        self.status_label.setText(f"❌ Erro: {erro}")
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
            str(Path("output").absolute() / "projeto.nc"),
            "Arquivos G-code (*.nc);;Todos os arquivos (*.*)"
        )
        
        if path:
            if self.gerador.salvar(self.gcode_atual, path):
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"✅ G-code salvo com sucesso!\n\n📁 {path}"
                )
                self.statusBar.showMessage(f"✅ Salvo: {Path(path).name}")
            else:
                QMessageBox.warning(self, "Erro", "❌ Erro ao salvar o arquivo")
    
    def _salvar_visualizacao(self):
        """Salva a visualização 3D como imagem"""
        if self.gcode_atual:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Visualização 3D",
                str(Path("output").absolute() / "visualizacao_3d.png"),
                "Imagem PNG (*.png);;Todos os arquivos (*.*)"
            )
            if path:
                self.visualizador_3d.salvar_imagem(path)
                QMessageBox.information(self, "Sucesso", f"📸 Visualização salva em:\n{path}")
                self.statusBar.showMessage(f"Visualização salva: {Path(path).name}")
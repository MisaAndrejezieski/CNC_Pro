"""Visualizador 3D do G-code usando matplotlib"""

import logging
import numpy as np
import re
from pathlib import Path
from typing import List, Tuple, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

# Importa matplotlib para 3D
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

logger = logging.getLogger(__name__)


class Visualizador3D(QWidget):
    """Widget para visualização 3D do G-code"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configura o layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Cria figura matplotlib
        self.figure = Figure(figsize=(10, 8), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(450)
        layout.addWidget(self.canvas)
        
        self.ax = None
        self.gcode_atual = None
        
        # Estilo escuro
        plt.style.use('dark_background')
    
    def carregar_gcode(self, gcode_lines: List[str], dimensoes: Tuple[float, float] = (100, 100)):
        """
        Carrega e visualiza o G-code em 3D
        
        Args:
            gcode_lines: Lista de linhas do G-code
            dimensoes: (largura, altura) em mm
        """
        self.gcode_atual = gcode_lines
        self._plotar_3d(gcode_lines, dimensoes)
    
    def _plotar_3d(self, gcode_lines: List[str], dimensoes: Tuple[float, float]):
        """Plota o caminho da ferramenta em 3D"""
        
        # Extrai coordenadas e movimentos
        x_coords = []
        y_coords = []
        z_coords = []
        tipos = []  # 'corte' ou 'rapido'
        
        x_atual, y_atual, z_atual = 0.0, 0.0, 5.0
        
        for linha in gcode_lines:
            # Ignora comentários e linhas vazias
            linha_limpa = linha.strip()
            if not linha_limpa or linha_limpa.startswith('(') or linha_limpa.startswith(';'):
                continue
            
            # Extrai coordenadas
            x_match = re.search(r'X([-+]?\d*\.?\d+)', linha_limpa)
            y_match = re.search(r'Y([-+]?\d*\.?\d+)', linha_limpa)
            z_match = re.search(r'Z([-+]?\d*\.?\d+)', linha_limpa)
            
            if x_match:
                x_atual = float(x_match.group(1))
            if y_match:
                y_atual = float(y_match.group(1))
            if z_match:
                z_atual = float(z_match.group(1))
            
            # Determina o tipo de movimento
            if linha_limpa.startswith('G0'):
                tipo = 'rapido'
            elif linha_limpa.startswith('G1'):
                tipo = 'corte'
            else:
                continue
            
            x_coords.append(x_atual)
            y_coords.append(y_atual)
            z_coords.append(z_atual)
            tipos.append(tipo)
        
        if not x_coords:
            logger.warning("Nenhum movimento encontrado no G-code")
            return
        
        # Limpa o gráfico anterior
        self.figure.clear()
        
        # Cria subplot 3D
        self.ax = self.figure.add_subplot(111, projection='3d')
        
        # Separa os pontos por segmentos contínuos
        pontos_x = []
        pontos_y = []
        pontos_z = []
        tipo_atual = None
        
        for i in range(len(x_coords)):
            if tipo_atual != tipos[i] and len(pontos_x) > 1:
                # Plota o segmento anterior
                cor = '#00ff00' if tipo_atual == 'corte' else '#888888'
                estilo = '-' if tipo_atual == 'corte' else '--'
                self.ax.plot(pontos_x, pontos_y, pontos_z, 
                            color=cor, linestyle=estilo, linewidth=1.5, alpha=0.8)
                pontos_x = []
                pontos_y = []
                pontos_z = []
            
            pontos_x.append(x_coords[i])
            pontos_y.append(y_coords[i])
            pontos_z.append(z_coords[i])
            tipo_atual = tipos[i]
        
        # Plota o último segmento
        if len(pontos_x) > 1:
            cor = '#00ff00' if tipo_atual == 'corte' else '#888888'
            estilo = '-' if tipo_atual == 'corte' else '--'
            self.ax.plot(pontos_x, pontos_y, pontos_z, 
                        color=cor, linestyle=estilo, linewidth=1.5, alpha=0.8)
        
        # Configura o gráfico
        self.ax.set_xlabel('X (mm)', color='white', fontsize=10)
        self.ax.set_ylabel('Y (mm)', color='white', fontsize=10)
        self.ax.set_zlabel('Z (mm)', color='white', fontsize=10)
        
        # Inverte Z para mostrar profundidade negativa corretamente
        self.ax.invert_zaxis()
        
        # Configura limites
        largura, altura = dimensoes
        self.ax.set_xlim(0, largura)
        self.ax.set_ylim(0, altura)
        
        # Configura aparência
        self.ax.set_title('Trajetória da Ferramenta - Visualização 3D', 
                         color='white', fontsize=12, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor('#2d2d30')
        
        # Adiciona legenda
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='#00ff00', linewidth=2, label='Corte (G1)'),
            Line2D([0], [0], color='#888888', linewidth=1, linestyle='--', label='Movimento Rápido (G0)'),
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', facecolor='#1e1e1e')
        
        # Adiciona pontos de profundidade
        z_vals = np.array(z_coords)
        if len(z_vals) > 0:
            min_z = np.min(z_vals)
            self.ax.scatter([largura * 0.9], [altura * 0.1], [min_z], 
                          color='red', s=50, marker='^', label=f'Profundidade máx: {abs(min_z):.1f}mm')
            self.ax.legend(loc='upper left', facecolor='#1e1e1e')
        
        # Ajusta a câmera para uma boa visualização
        self.ax.view_init(elev=25, azim=-60)
        
        # Ajusta layout
        self.figure.tight_layout()
        
        # Atualiza o canvas
        self.canvas.draw()
    
    def limpar(self):
        """Limpa a visualização"""
        self.figure.clear()
        self.canvas.draw()
    
    def salvar_imagem(self, caminho: str):
        """Salva a visualização como imagem"""
        if caminho:
            self.figure.savefig(caminho, dpi=150, bbox_inches='tight', 
                              facecolor='#1e1e1e', edgecolor='none')
            logger.info(f"Visualização salva: {caminho}")
            return True
        return False
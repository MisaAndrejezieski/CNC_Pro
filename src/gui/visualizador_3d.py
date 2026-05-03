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
        self.figure = Figure(figsize=(8, 6), facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(400)
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
        colors = []
        
        x_atual, y_atual, z_atual = 0.0, 0.0, 5.0  # Z seguro inicial
        
        ultimo_movimento = None
        
        for linha in gcode_lines:
            # Ignora comentários
            if linha.startswith('(') or linha.startswith(';'):
                continue
            
            # Extrai coordenadas
            x_match = re.search(r'X([-+]?\d*\.?\d+)', linha)
            y_match = re.search(r'Y([-+]?\d*\.?\d+)', linha)
            z_match = re.search(r'Z([-+]?\d*\.?\d+)', linha)
            
            if x_match:
                x_atual = float(x_match.group(1))
            if y_match:
                y_atual = float(y_match.group(1))
            if z_match:
                z_atual = float(z_match.group(1))
            
            # Determina o tipo de movimento
            if linha.startswith('G0'):
                cor = 'green'  # Movimento rápido
                estilo = '--'
            elif linha.startswith('G1'):
                cor = 'red'    # Corte
                estilo = '-'
            else:
                continue
            
            # Adiciona pontos
            x_coords.append(x_atual)
            y_coords.append(y_atual)
            z_coords.append(z_atual)
            colors.append(cor)
        
        # Limpa o gráfico anterior
        self.figure.clear()
        
        # Cria subplot 3D
        self.ax = self.figure.add_subplot(111, projection='3d')
        
        # Plota os pontos
        if len(x_coords) > 1:
            # Separa por segmentos de movimento
            pontos_x = []
            pontos_y = []
            pontos_z = []
            
            for i in range(len(x_coords)):
                pontos_x.append(x_coords[i])
                pontos_y.append(y_coords[i])
                pontos_z.append(z_coords[i])
                
                # Plota a cada ponto ou no final
                if len(pontos_x) > 1:
                    cor = 'cyan' if z_coords[i] < 0 else 'gray'
                    self.ax.plot(pontos_x, pontos_y, pontos_z, 
                                color=cor, linewidth=1.5, alpha=0.8)
                    pontos_x = [x_coords[i]]
                    pontos_y = [y_coords[i]]
                    pontos_z = [z_coords[i]]
        
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
        
        # Adiciona legenda manual
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color='cyan', linewidth=2, label='Corte (G1)'),
            Line2D([0], [0], color='gray', linewidth=1, linestyle='--', label='Movimento Rápido (G0)'),
        ]
        self.ax.legend(handles=legend_elements, loc='upper right', facecolor='#1e1e1e')
        
        # Ajusta a câmera para uma boa visualização
        self.ax.view_init(elev=25, azim=-60)
        
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


class Visualizador3DSimples:
    """Versão simplificada para visualização rápida"""
    
    @staticmethod
    def visualizar(gcode_lines: List[str], dimensoes: Tuple[float, float] = (100, 100)):
        """Abre uma janela separada com visualização 3D"""
        
        # Extrai pontos
        x_coords, y_coords, z_coords = [], [], []
        x, y, z = 0, 0, 5
        
        for linha in gcode_lines:
            if linha.startswith('(') or linha.startswith(';'):
                continue
            
            x_match = re.search(r'X([-+]?\d*\.?\d+)', linha)
            y_match = re.search(r'Y([-+]?\d*\.?\d+)', linha)
            z_match = re.search(r'Z([-+]?\d*\.?\d+)', linha)
            
            if x_match:
                x = float(x_match.group(1))
            if y_match:
                y = float(y_match.group(1))
            if z_match:
                z = float(z_match.group(1))
            
            if linha.startswith('G1'):  # Apenas movimentos de corte
                x_coords.append(x)
                y_coords.append(y)
                z_coords.append(z)
        
        if not x_coords:
            print("Nenhum movimento de corte encontrado")
            return
        
        # Cria figura
        fig = plt.figure(figsize=(12, 8), facecolor='#1e1e1e')
        ax = fig.add_subplot(111, projection='3d')
        
        # Plota
        scatter = ax.scatter(x_coords, y_coords, z_coords, 
                           c=z_coords, cmap='coolwarm', s=10, alpha=0.7)
        
        # Configura
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.set_title('Visualização 3D do G-code')
        ax.invert_zaxis()
        
        # Barra de cores
        plt.colorbar(scatter, ax=ax, label='Profundidade Z (mm)')
        
        plt.tight_layout()
        plt.show()
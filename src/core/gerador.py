"""Módulo de geração de G-code a partir de imagens"""

import logging
import numpy as np
from PIL import Image, ImageFilter
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConfigGerador:
    """Configuração completa do gerador"""
    passos_por_mm: float = 10.0
    profundidade_max_corte: float = 0.5
    altura_seguranca_z: float = 5.0
    velocidade_corte: float = 800.0
    velocidade_rapida: float = 3500.0
    limiar_preto_branco: int = 128
    diametro_ferramenta: float = 0.4
    sobreposicao: float = 0.4
    suavizar_imagem: bool = False
    blur_radius: float = 1.0
    inverter_cores: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConfigGerador':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class GeradorGCode:
    """Gerador profissional de G-code a partir de imagens"""
    
    def __init__(self, config: Dict[str, Any]):
        """Inicializa o gerador com configurações"""
        gerador_config = config.get('gerador', {})
        self.config = ConfigGerador(
            passos_por_mm=gerador_config.get('passos_por_mm', 10.0),
            profundidade_max_corte=gerador_config.get('profundidade_max_corte', 0.5),
            altura_seguranca_z=gerador_config.get('altura_seguranca_z', 5.0),
            velocidade_corte=gerador_config.get('velocidade_corte', 800.0),
            velocidade_rapida=gerador_config.get('velocidade_rapida', 3500.0),
            limiar_preto_branco=gerador_config.get('limiar_preto_branco', 128),
            diametro_ferramenta=gerador_config.get('diametro_ferramenta', 0.4),
            sobreposicao=gerador_config.get('sobreposicao', 0.4),
            suavizar_imagem=gerador_config.get('suavizar_imagem', False),
            blur_radius=gerador_config.get('blur_radius', 1.0),
            inverter_cores=gerador_config.get('inverter_cores', False)
        )
        self.passo_mm = 1.0 / self.config.passos_por_mm
        logger.info(f"Gerador inicializado: {self.config.passos_por_mm} passos/mm")
    
    def gerar(self, imagem_path: str, dimensoes_mm: Tuple[float, float], 
              profundidade_total: float = -1.0) -> Optional[List[str]]:
        """
        Gera G-code a partir de uma imagem
        
        Args:
            imagem_path: Caminho da imagem
            dimensoes_mm: (largura, altura) em mm
            profundidade_total: Profundidade em mm (negativa)
        
        Returns:
            Lista de strings com G-code ou None
        """
        try:
            # Carrega e processa imagem
            imagem = self._carregar_imagem(imagem_path, dimensoes_mm)
            if imagem is None:
                return None
            
            # Converte para binário
            imagem_binaria = self._binarizar_imagem(imagem)
            
            # Calcula passes
            profundidade_total = -abs(profundidade_total)
            num_passes, profundidades = self._calcular_passes(profundidade_total)
            
            logger.info(f"Gerando {num_passes} passes, profundidade final: {profundidade_total}mm")
            
            # Gera G-code
            gcode = []
            gcode.extend(self._gerar_cabecalho(dimensoes_mm, profundidade_total))
            
            for i, z in enumerate(profundidades, 1):
                gcode.extend(self._gerar_passagem(imagem_binaria, z, i, num_passes))
            
            gcode.extend(self._gerar_rodape())
            
            logger.info(f"G-code gerado: {len(gcode)} linhas")
            return gcode
            
        except FileNotFoundError:
            logger.error(f"Arquivo não encontrado: {imagem_path}")
            return None
        except Exception as e:
            logger.error(f"Erro ao gerar G-code: {e}", exc_info=True)
            return None
    
    def _carregar_imagem(self, path: str, dimensoes: Tuple[float, float]) -> Optional[np.ndarray]:
        """Carrega e redimensiona imagem"""
        try:
            img = Image.open(path)
            
            # Converte para grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Redimensiona baseado na resolução
            largura_mm, altura_mm = dimensoes
            largura_px = max(1, int(largura_mm * self.config.passos_por_mm))
            altura_px = max(1, int(altura_mm * self.config.passos_por_mm))
            
            img = img.resize((largura_px, altura_px), Image.Resampling.LANCZOS)
            
            # Suavização opcional
            if self.config.suavizar_imagem:
                img = img.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
            
            # Inversão opcional
            if self.config.inverter_cores:
                img = Image.fromarray(255 - np.array(img))
            
            return np.array(img, dtype=np.uint8)
            
        except Exception as e:
            logger.error(f"Erro ao carregar imagem {path}: {e}")
            return None
    
    def _binarizar_imagem(self, imagem: np.ndarray) -> np.ndarray:
        """Converte imagem para binário (corte ou não corte)"""
        return imagem < self.config.limiar_preto_branco
    
    def _calcular_passes(self, profundidade_total: float) -> Tuple[int, List[float]]:
        """Calcula passes de profundidade"""
        if profundidade_total >= 0:
            return 1, [0.0]
        
        profundidade_total = abs(profundidade_total)
        num_passes = int(np.ceil(profundidade_total / self.config.profundidade_max_corte))
        
        # Distribui profundidade igualmente entre os passes
        incremento = profundidade_total / num_passes
        profundidades = [-incremento * i for i in range(1, num_passes + 1)]
        
        return num_passes, profundidades
    
    def _gerar_cabecalho(self, dimensoes: Tuple[float, float], 
                         profundidade: float) -> List[str]:
        """Gera cabeçalho do G-code"""
        largura, altura = dimensoes
        return [
            "(CNC Pro - G-code Gerado Automaticamente)",
            f"(Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            f"(Dimensões: {largura:.2f} x {altura:.2f} mm)",
            f"(Profundidade final: {abs(profundidade):.2f} mm)",
            f"(Resolução: {self.config.passos_por_mm:.1f} passos/mm)",
            f"(Ferramenta: {self.config.diametro_ferramenta:.2f} mm)",
            "",
            "G90 ; Coordenadas absolutas",
            "G21 ; Unidades em milímetros",
            f"M3 S10000 ; Liga spindle",
            f"G0 Z{self.config.altura_seguranca_z:.3f} F{self.config.velocidade_rapida:.1f}",
            "G0 X0 Y0",
            ""
        ]
    
    def _gerar_passagem(self, imagem: np.ndarray, z_atual: float, 
                       passe: int, total: int) -> List[str]:
        """Gera uma passagem de corte"""
        altura, largura = imagem.shape
        gcode = [
            f"(Passe {passe}/{total} - Profundidade Z: {z_atual:.3f} mm)",
            f"F{self.config.velocidade_corte:.1f}"
        ]
        
        em_corte = False
        
        for y in range(altura):
            # Zig-zag: alterna direção a cada linha para otimizar
            if y % 2 == 0:
                x_range = range(largura)
            else:
                x_range = range(largura - 1, -1, -1)
            
            for x in x_range:
                if imagem[y, x]:  # Pixel que deve ser cortado
                    x_mm = x * self.passo_mm
                    y_mm = y * self.passo_mm
                    
                    if not em_corte:
                        # Move rapidamente para posição e desce a ferramenta
                        gcode.append(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
                        gcode.append(f"G1 Z{z_atual:.3f}")
                        em_corte = True
                    else:
                        # Continua cortando em linha reta
                        gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f}")
                elif em_corte:
                    # Termina o corte atual e sobe a ferramenta
                    gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
                    em_corte = False
        
        # Garante que a ferramenta está levantada no final do passe
        if em_corte:
            gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
        
        return gcode
    
    def _gerar_rodape(self) -> List[str]:
        """Gera rodapé do G-code"""
        return [
            "",
            "M5 ; Desliga spindle",
            f"G0 Z{self.config.altura_seguranca_z:.3f} F{self.config.velocidade_rapida:.1f}",
            "G0 X0 Y0 ; Retorna à origem",
            "M30 ; Fim do programa"
        ]
    
    def salvar(self, gcode: List[str], caminho: str) -> bool:
        """Salva G-code em arquivo"""
        try:
            path = Path(caminho)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(gcode))
            
            logger.info(f"G-code salvo com sucesso: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar G-code: {e}")
            return False
    
    def analisar_gcode(self, gcode: List[str]) -> Dict:
        """Analisa o G-code gerado e retorna estatísticas"""
        stats = {
            'total_linhas': len(gcode),
            'movimentos_rapidos': 0,
            'movimentos_corte': 0,
            'profundidade_maxima': 0,
            'distancia_total': 0.0
        }
        
        ultimo_x, ultimo_y = None, None
        
        for linha in gcode:
            if linha.startswith('G0'):
                stats['movimentos_rapidos'] += 1
            elif linha.startswith('G1'):
                stats['movimentos_corte'] += 1
                
                # Extrai coordenadas
                x_match = __import__('re').search(r'X([-+]?\d*\.?\d+)', linha)
                y_match = __import__('re').search(r'Y([-+]?\d*\.?\d+)', linha)
                z_match = __import__('re').search(r'Z([-+]?\d*\.?\d+)', linha)
                
                if z_match:
                    z = float(z_match.group(1))
                    stats['profundidade_maxima'] = min(stats['profundidade_maxima'], z)
                
                if x_match and y_match and ultimo_x is not None:
                    x, y = float(x_match.group(1)), float(y_match.group(1))
                    stats['distancia_total'] += np.hypot(x - ultimo_x, y - ultimo_y)
                    ultimo_x, ultimo_y = x, y
                elif x_match and y_match:
                    ultimo_x, ultimo_y = float(x_match.group(1)), float(y_match.group(1))
        
        return stats
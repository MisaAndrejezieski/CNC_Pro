"""Módulo de geração de G-code a partir de imagens"""

import logging
import numpy as np
from PIL import Image
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class EstrategiaVarredura(Enum):
    """Estratégias de varredura para usinagem"""
    ZIG_ZAG = "zig_zag"
    LINHA_UNICA = "linha_unica"
    ESPIRAL = "espiral"
    OTIMIZADO = "otimizado"


@dataclass
class ConfigGerador:
    """Configuração completa do gerador"""
    # Resolução
    passos_por_mm: float = 10.0
    
    # Profundidade
    profundidade_max_corte: float = 0.5
    altura_seguranca_z: float = 5.0
    
    # Velocidades
    velocidade_corte: float = 800.0
    velocidade_rapida: float = 3500.0
    
    # Ferramenta
    diametro_ferramenta: float = 0.4
    sobreposicao: float = 0.4  # % de sobreposição entre passes
    
    # Processamento
    limiar_preto_branco: int = 128
    estrategia_varredura: str = "zig_zag"
    otimizar_caminho: bool = True
    inverter_direcao: bool = True
    
    # Pré-processamento
    suavizar_imagem: bool = False
    blur_radius: float = 1.0
    inverter_cores: bool = False
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConfigGerador':
        """Cria configuração a partir de dicionário"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class GeradorGCode:
    """Gerador profissional de G-code"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa o gerador
        
        Args:
            config: Dicionário com configurações
        """
        self.config = ConfigGerador.from_dict(config.get('gerador', {}))
        self.passo_mm = 1.0 / self.config.passos_por_mm
        
        logger.info(f"Gerador inicializado: resolução={self.config.passos_por_mm} passos/mm")
    
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
                gcode.extend(self._gerar_passagem(
                    imagem_binaria, z, i, num_passes,
                    dimensoes_mm
                ))
            
            gcode.extend(self._gerar_rodape())
            
            logger.info(f"G-code gerado: {len(gcode)} linhas")
            return gcode
            
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
            "(CNC Pro G-code Gerado)",
            f"(Data: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            f"(Dimensões: {largura:.2f}x{altura:.2f} mm)",
            f"(Profundidade: {abs(profundidade):.2f} mm)",
            f"(Ferramenta: {self.config.diametro_ferramenta:.2f} mm)",
            f"(Resolução: {self.config.passos_por_mm:.1f} passos/mm)",
            "",
            "G90 ; Coordenadas absolutas",
            "G21 ; Unidades mm",
            f"M3 S10000 ; Liga spindle",
            f"G0 Z{self.config.altura_seguranca_z:.3f} F{self.config.velocidade_rapida:.1f}",
            "G0 X0 Y0",
            ""
        ]
    
    def _gerar_rodape(self) -> List[str]:
        """Gera rodapé do G-code"""
        return [
            "",
            "M5 ; Desliga spindle",
            f"G0 Z{self.config.altura_seguranca_z:.3f} F{self.config.velocidade_rapida:.1f}",
            "G0 X0 Y0",
            "M30 ; Fim do programa"
        ]
    
    def _gerar_passagem(self, imagem: np.ndarray, z_atual: float, 
                       passe: int, total: int, dimensoes: Tuple[float, float]) -> List[str]:
        """Gera uma passagem de corte"""
        
        altura_px, largura_px = imagem.shape
        gcode = [
            f"(Passe {passe}/{total} - Z: {z_atual:.3f} mm)",
            f"F{self.config.velocidade_corte:.1f}"
        ]
        
        em_corte = False
        
        for y in range(altura_px):
            # Zig-zag alternado para otimizar
            if y % 2 == 0:
                x_range = range(largura_px)
            else:
                x_range = range(largura_px - 1, -1, -1)
            
            for x in x_range:
                if imagem[y, x]:  # Pixel ativo (cortar)
                    x_mm = x * self.passo_mm
                    y_mm = y * self.passo_mm
                    
                    if not em_corte:
                        # Inicia corte
                        gcode.append(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
                        gcode.append(f"G1 Z{z_atual:.3f}")
                        em_corte = True
                    else:
                        # Continua corte
                        gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f}")
                elif em_corte:
                    # Finaliza corte
                    gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
                    em_corte = False
        
        # Garante que terminou com ferramenta levantada
        if em_corte:
            gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
        
        return gcode
    
    def salvar(self, gcode: List[str], caminho: str) -> bool:
        """Salva G-code em arquivo"""
        try:
            path = Path(caminho)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(gcode))
            
            logger.info(f"G-code salvo: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar G-code: {e}")
            return False
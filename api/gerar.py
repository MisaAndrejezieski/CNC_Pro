"""
API Serverless para Vercel
Endpoint de geração de G-code
"""

import base64
import json
import re
import sys
import os
from pathlib import Path
from io import BytesIO

# Adiciona o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
import numpy as np


class ConfigGerador:
    """Configuração do gerador"""
    def __init__(self, config_dict):
        self.passos_por_mm = config_dict.get('passos_por_mm', 10.0)
        self.profundidade_max_corte = config_dict.get('profundidade_max_corte', 0.5)
        self.altura_seguranca_z = config_dict.get('altura_seguranca_z', 5.0)
        self.velocidade_corte = config_dict.get('velocidade_corte', 800.0)
        self.velocidade_rapida = config_dict.get('velocidade_rapida', 3500.0)
        self.limiar_preto_branco = config_dict.get('limiar_preto_branco', 128)
        self.diametro_ferramenta = config_dict.get('diametro_ferramenta', 0.4)


class GeradorGCode:
    """Gerador de G-code para serverless"""
    
    def __init__(self, config):
        self.config = ConfigGerador(config)
        self.passo_mm = 1.0 / self.config.passos_por_mm
    
    def gerar(self, imagem_data, dimensoes_mm, profundidade_total):
        """Gera G-code a partir de dados da imagem"""
        try:
            # Carrega imagem do base64
            if ',' in imagem_data:
                imagem_data = imagem_data.split(',')[1]
            
            img_bytes = base64.b64decode(imagem_data)
            img = Image.open(BytesIO(img_bytes)).convert('L')
            
            largura_mm, altura_mm = dimensoes_mm
            
            # Redimensiona
            largura_px = max(1, int(largura_mm * self.config.passos_por_mm))
            altura_px = max(1, int(altura_mm * self.config.passos_por_mm))
            img = img.resize((largura_px, altura_px), Image.Resampling.LANCZOS)
            
            # Binariza
            pixels = np.array(img)
            binario = pixels < self.config.limiar_preto_branco
            
            # Calcula passes
            profundidade_total = -abs(profundidade_total)
            num_passes = max(1, int(np.ceil(abs(profundidade_total) / self.config.profundidade_max_corte)))
            incremento = abs(profundidade_total) / num_passes
            
            # Gera G-code
            gcode = self._gerar_cabecalho(dimensoes_mm, profundidade_total)
            
            for i in range(1, num_passes + 1):
                z = -incremento * i
                gcode.extend(self._gerar_passagem(binario, z, i, num_passes))
            
            gcode.extend(self._gerar_rodape())
            
            return gcode
            
        except Exception as e:
            raise Exception(f"Erro ao gerar G-code: {str(e)}")
    
    def _gerar_cabecalho(self, dimensoes, profundidade):
        from datetime import datetime
        largura, altura = dimensoes
        return [
            "(CNC Pro - G-code Gerado Online)",
            f"(Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})",
            f"(Dimensões: {largura:.2f} x {altura:.2f} mm)",
            f"(Profundidade: {abs(profundidade):.2f} mm)",
            "",
            "G90 G21",
            f"M3 S10000",
            f"G0 Z{self.config.altura_seguranca_z:.3f} F{self.config.velocidade_rapida:.1f}",
            "G0 X0 Y0",
            ""
        ]
    
    def _gerar_passagem(self, imagem, z_atual, passe, total):
        altura, largura = imagem.shape
        gcode = [
            f"(Passe {passe}/{total} Z: {z_atual:.3f} mm)",
            f"F{self.config.velocidade_corte:.1f}"
        ]
        
        em_corte = False
        
        for y in range(altura):
            if y % 2 == 0:
                x_range = range(largura)
            else:
                x_range = range(largura - 1, -1, -1)
            
            for x in x_range:
                if imagem[y, x]:
                    x_mm = x * self.passo_mm
                    y_mm = y * self.passo_mm
                    
                    if not em_corte:
                        gcode.append(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
                        gcode.append(f"G1 Z{z_atual:.3f}")
                        em_corte = True
                    else:
                        gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f}")
                elif em_corte:
                    gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
                    em_corte = False
        
        if em_corte:
            gcode.append(f"G0 Z{self.config.altura_seguranca_z:.3f}")
        
        return gcode
    
    def _gerar_rodape(self):
        return [
            "",
            "M5",
            f"G0 Z{self.config.altura_seguranca_z:.3f}",
            "G0 X0 Y0",
            "M30"
        ]


def handler(request, context):
    """
    Função principal do Vercel Serverless Function
    """
    # Configura CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }
    
    # Resposta para preflight (OPTIONS)
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Apenas POST é permitido
    if request.method != 'POST':
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'success': False, 'error': 'Método não permitido'})
        }
    
    try:
        # Parse do body
        body = json.loads(request.body)
        
        imagem = body.get('imagem')
        largura = float(body.get('largura', 100))
        altura = float(body.get('altura', 100))
        profundidade = float(body.get('profundidade', 3))
        resolucao = float(body.get('resolucao', 10))
        limiar = int(body.get('limiar', 128))
        
        if not imagem:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'success': False, 'error': 'Nenhuma imagem fornecida'})
            }
        
        # Configura o gerador
        config = {
            'passos_por_mm': resolucao,
            'profundidade_max_corte': 0.5,
            'altura_seguranca_z': 5.0,
            'velocidade_corte': 800,
            'velocidade_rapida': 3500,
            'limiar_preto_branco': limiar,
            'diametro_ferramenta': 0.4
        }
        
        gerador = GeradorGCode(config)
        
        # Gera o G-code
        gcode = gerador.gerar(imagem, (largura, altura), -profundidade)
        
        # Analisa estatísticas
        movimentos_corte = len([l for l in gcode if l.startswith('G1')])
        movimentos_rapidos = len([l for l in gcode if l.startswith('G0')])
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'gcode': '\n'.join(gcode),
                'linhas': len(gcode),
                'movimentos_corte': movimentos_corte,
                'movimentos_rapidos': movimentos_rapidos
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'success': False, 'error': str(e)})
        }
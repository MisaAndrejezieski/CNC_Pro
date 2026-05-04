"""
CNC Pro - Versão Web
Execute com: python web_app.py
Acesse: http://localhost:5000
"""

import os
import json
import base64
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import numpy as np
from PIL import Image

# Importa o gerador
from src.core.gerador import GeradorGCode

app = Flask(__name__)
CORS(app)

# Configurações
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'nc', 'gcode'}

# Cria pastas necessárias
Path('uploads').mkdir(exist_ok=True)
Path('output').mkdir(exist_ok=True)
Path('static').mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/gerar', methods=['POST'])
def gerar_gcode():
    """Endpoint para gerar G-code a partir de imagem"""
    try:
        # Recebe os dados
        data = request.json
        imagem_base64 = data.get('imagem')
        largura = float(data.get('largura', 100))
        altura = float(data.get('altura', 100))
        profundidade = float(data.get('profundidade', 3))
        resolucao = float(data.get('resolucao', 10))
        limiar = int(data.get('limiar', 128))
        
        # Decodifica a imagem
        imagem_data = base64.b64decode(imagem_base64.split(',')[1])
        imagem_path = Path('uploads/temp_image.png')
        with open(imagem_path, 'wb') as f:
            f.write(imagem_data)
        
        # Configura o gerador
        config = {
            'gerador': {
                'passos_por_mm': resolucao,
                'profundidade_max_corte': 0.5,
                'altura_seguranca_z': 5.0,
                'velocidade_corte': 800,
                'velocidade_rapida': 3500,
                'limiar_preto_branco': limiar,
                'diametro_ferramenta': 0.4
            }
        }
        
        gerador = GeradorGCode(config)
        
        # Gera o G-code
        gcode = gerador.gerar(
            str(imagem_path),
            (largura, altura),
            -profundidade
        )
        
        if gcode:
            # Salva o arquivo
            output_path = Path('output/gerado.nc')
            gerador.salvar(gcode, str(output_path))
            
            # Limpa arquivo temporário
            imagem_path.unlink()
            
            return jsonify({
                'success': True,
                'gcode': '\n'.join(gcode),
                'linhas': len(gcode),
                'arquivo': str(output_path)
            })
        else:
            return jsonify({'success': False, 'error': 'Erro ao gerar G-code'})
            
    except Exception as e:
        logger.error(f"Erro: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/analisar', methods=['POST'])
def analisar_gcode():
    """Endpoint para analisar um arquivo G-code"""
    try:
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Arquivo vazio'})
        
        if arquivo and allowed_file(arquivo.filename):
            filename = secure_filename(arquivo.filename)
            filepath = Path('uploads') / filename
            arquivo.save(filepath)
            
            # Lê o G-code
            with open(filepath, 'r') as f:
                linhas = f.readlines()
            
            # Analisa
            stats = analisar_linhas_gcode(linhas)
            
            # Limpa arquivo
            filepath.unlink()
            
            return jsonify({
                'success': True,
                'stats': stats,
                'gcode': ''.join(linhas[:50])  # Primeiras 50 linhas
            })
        
        return jsonify({'success': False, 'error': 'Tipo de arquivo não permitido'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def analisar_linhas_gcode(linhas):
    """Analisa linhas de G-code"""
    import re
    
    stats = {
        'total_linhas': len(linhas),
        'movimentos_corte': 0,
        'movimentos_rapidos': 0,
        'profundidade_max': 0,
        'limites': {'x_min': 0, 'x_max': 0, 'y_min': 0, 'y_max': 0, 'z_min': 0, 'z_max': 0}
    }
    
    x_min = y_min = z_min = float('inf')
    x_max = y_max = z_max = float('-inf')
    
    for linha in linhas:
        linha_upper = linha.upper()
        
        if linha_upper.startswith('G0'):
            stats['movimentos_rapidos'] += 1
        elif linha_upper.startswith('G1'):
            stats['movimentos_corte'] += 1
        
        # Extrai coordenadas
        x_match = re.search(r'X([-+]?\d*\.?\d+)', linha_upper)
        y_match = re.search(r'Y([-+]?\d*\.?\d+)', linha_upper)
        z_match = re.search(r'Z([-+]?\d*\.?\d+)', linha_upper)
        
        if x_match:
            x = float(x_match.group(1))
            x_min, x_max = min(x_min, x), max(x_max, x)
        if y_match:
            y = float(y_match.group(1))
            y_min, y_max = min(y_min, y), max(y_max, y)
        if z_match:
            z = float(z_match.group(1))
            z_min, z_max = min(z_min, z), max(z_max, z)
            stats['profundidade_max'] = min(stats['profundidade_max'], z)
    
    stats['limites'] = {
        'x_min': x_min if x_min != float('inf') else 0,
        'x_max': x_max if x_max != float('-inf') else 100,
        'y_min': y_min if y_min != float('inf') else 0,
        'y_max': y_max if y_max != float('-inf') else 100,
        'z_min': z_min if z_min != float('inf') else -5,
        'z_max': z_max if z_max != float('-inf') else 5
    }
    
    return stats


@app.route('/api/baixar', methods=['GET'])
def baixar_gcode():
    """Download do último G-code gerado"""
    output_path = Path('output/gerado.nc')
    if output_path.exists():
        return send_file(output_path, as_attachment=True, download_name='projeto_cnc.nc')
    return jsonify({'success': False, 'error': 'Arquivo não encontrado'})


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 CNC Pro - Servidor Web Iniciado!")
    print("📱 Acesse no navegador: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
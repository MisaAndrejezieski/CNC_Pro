"""
API Serverless para Vercel
Endpoint de geração de G-code
"""

import base64
import json
from io import BytesIO
from PIL import Image
import re

def handler(request, context):
    """Função principal do Vercel Serverless Function"""
    
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
        
        # Decodifica a imagem
        if ',' in imagem:
            imagem = imagem.split(',')[1]
        
        img_bytes = base64.b64decode(imagem)
        img = Image.open(BytesIO(img_bytes)).convert('L')
        
        # Redimensiona
        passo = 1.0 / resolucao
        largura_px = max(1, int(largura * resolucao))
        altura_px = max(1, int(altura * resolucao))
        img = img.resize((largura_px, altura_px), Image.Resampling.LANCZOS)
        
        # Binariza
        pixels = img.getdata()
        binario = [p < limiar for p in pixels]
        
        # Gera G-code
        gcode = []
        gcode.append(f"(CNC Pro - G-code Gerado Online)")
        gcode.append(f"(Dimensões: {largura:.2f} x {altura:.2f} mm)")
        gcode.append(f"(Profundidade: {profundidade:.2f} mm)")
        gcode.append(f"(Resolução: {resolucao:.0f} passos/mm)")
        gcode.append("")
        gcode.append("G90 G21")
        gcode.append("M3 S10000")
        gcode.append("G0 Z5.000 F3500.0")
        gcode.append("G0 X0 Y0")
        gcode.append("")
        
        # Calcula passes
        profundidade_corte = 0.5
        num_passes = max(1, int(profundidade / profundidade_corte))
        passes_profundidade = [-(profundidade / num_passes) * i for i in range(1, num_passes + 1)]
        
        movimento_corte = 0
        movimento_rapido = 0
        
        for i, z in enumerate(passes_profundidade, 1):
            gcode.append(f"(Passe {i}/{num_passes} Z: {z:.3f} mm)")
            gcode.append(f"F800.0")
            
            em_corte = False
            
            for y in range(altura_px):
                if y % 2 == 0:
                    x_range = range(largura_px)
                else:
                    x_range = range(largura_px - 1, -1, -1)
                
                for x in x_range:
                    idx = y * largura_px + x
                    if idx < len(binario) and binario[idx]:
                        x_mm = x * passo
                        y_mm = y * passo
                        
                        if not em_corte:
                            gcode.append(f"G0 X{x_mm:.3f} Y{y_mm:.3f}")
                            gcode.append(f"G1 Z{z:.3f}")
                            em_corte = True
                            movimento_rapido += 1
                            movimento_corte += 1
                        else:
                            gcode.append(f"G1 X{x_mm:.3f} Y{y_mm:.3f}")
                            movimento_corte += 1
                    elif em_corte:
                        gcode.append(f"G0 Z5.000")
                        em_corte = False
                        movimento_rapido += 1
            
            if em_corte:
                gcode.append(f"G0 Z5.000")
                movimento_rapido += 1
        
        gcode.append("")
        gcode.append("M5")
        gcode.append("G0 Z5.000")
        gcode.append("G0 X0 Y0")
        gcode.append("M30")
        
        total_linhas = len(gcode)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'gcode': '\n'.join(gcode),
                'linhas': total_linhas,
                'movimentos_corte': movimento_corte,
                'movimentos_rapidos': movimento_rapido
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'success': False, 'error': str(e)})
        }
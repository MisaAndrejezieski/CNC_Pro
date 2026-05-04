from http.server import BaseHTTPRequestHandler
import json
import base64
from io import BytesIO
from PIL import Image

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        # CORS headers
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Pega o tamanho do corpo
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            
            imagem = body.get('imagem')
            largura = float(body.get('largura', 100))
            altura = float(body.get('altura', 100))
            profundidade = float(body.get('profundidade', 3))
            resolucao = float(body.get('resolucao', 10))
            limiar = int(body.get('limiar', 128))
            
            # Decodifica imagem
            if ',' in imagem:
                imagem = imagem.split(',')[1]
            img_bytes = base64.b64decode(imagem)
            img = Image.open(BytesIO(img_bytes)).convert('L')
            
            # Redimensiona
            largura_px = max(1, int(largura * resolucao))
            altura_px = max(1, int(altura * resolucao))
            img = img.resize((largura_px, altura_px))
            
            # Binariza
            pixels = img.getdata()
            binario = [p < limiar for p in pixels]
            passo = 1.0 / resolucao
            
            # Gera G-code
            gcode = []
            gcode.append(f"(CNC Pro)")
            gcode.append(f"(Largura: {largura}mm, Altura: {altura}mm)")
            gcode.append(f"(Profundidade: {profundidade}mm)")
            gcode.append("G90 G21")
            gcode.append("G0 Z5.0")
            gcode.append("G0 X0 Y0")
            
            num_passes = max(1, int(profundidade / 0.5))
            incremento = profundidade / num_passes
            
            for p in range(1, num_passes + 1):
                z = -incremento * p
                gcode.append(f"(Passe {p}/{num_passes} Z={z:.2f})")
                gcode.append("F800")
                
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
                            gcode.append(f"G1 X{x_mm:.2f} Y{y_mm:.2f}")
                            gcode.append(f"Z{z:.2f}")
            
            gcode.append("G0 Z5.0")
            gcode.append("G0 X0 Y0")
            gcode.append("M30")
            
            resultado = {
                'success': True,
                'gcode': '\n'.join(gcode),
                'linhas': len(gcode)
            }
            
            self.wfile.write(json.dumps(resultado).encode('utf-8'))
            
        except Exception as e:
            resultado = {
                'success': False,
                'error': str(e)
            }
            self.wfile.write(json.dumps(resultado).encode('utf-8'))
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'API CNC Pro is running! Use POST method to generate G-code.')
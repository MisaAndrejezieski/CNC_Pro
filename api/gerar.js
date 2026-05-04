// api/gerar.js - Processamento REAL da imagem

export default async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    if (req.method !== 'POST') {
        return res.status(405).json({ success: false, error: 'Use POST' });
    }
    
    try {
        const { 
            imagem, 
            largura = 100, 
            altura = 100, 
            profundidade = 3,
            resolucao = 10,
            limiar = 128 
        } = req.body;
        
        if (!imagem) {
            return res.status(400).json({ success: false, error: 'Nenhuma imagem fornecida' });
        }
        
        // Processa a imagem usando canvas
        const { createCanvas, loadImage } = await import('canvas');
        
        // Decodifica a imagem base64
        const base64Data = imagem.split(',')[1];
        const imageBuffer = Buffer.from(base64Data, 'base64');
        
        // Carrega a imagem
        const img = await loadImage(imageBuffer);
        
        // Calcula dimensões em pixels baseado na resolução
        const passosPorMm = resolucao;
        const larguraPx = Math.max(1, Math.floor(largura * passosPorMm));
        const alturaPx = Math.max(1, Math.floor(altura * passosPorMm));
        
        // Redimensiona a imagem para as dimensões de corte
        const canvas = createCanvas(larguraPx, alturaPx);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, larguraPx, alturaPx);
        
        // Obtém os pixels
        const imageData = ctx.getImageData(0, 0, larguraPx, alturaPx);
        const pixels = imageData.data;
        
        // Calcula o passo em mm por pixel
        const passoX = largura / larguraPx;
        const passoY = altura / alturaPx;
        
        // Gera o G-code baseado na imagem
        const gcode = [];
        const dataHora = new Date().toLocaleString('pt-BR');
        
        gcode.push(`(CNC Pro - G-code Gerado a partir da Imagem)`);
        gcode.push(`(Data: ${dataHora})`);
        gcode.push(`(Dimensões: ${largura} x ${altura} mm)`);
        gcode.push(`(Profundidade: ${profundidade} mm)`);
        gcode.push(`(Resolução: ${resolucao} passos/mm)`);
        gcode.push(`(Limiar: ${limiar})`);
        gcode.push(`(Dimensões imagem: ${larguraPx} x ${alturaPx} pixels)`);
        gcode.push(``);
        gcode.push(`G90 ; Coordenadas absolutas`);
        gcode.push(`G21 ; Unidades em mm`);
        gcode.push(`M3 S10000 ; Liga spindle`);
        gcode.push(`G0 Z5.000 ; Altura de segurança`);
        gcode.push(`G0 X0 Y0 ; Home`);
        gcode.push(``);
        
        // Calcula passes de profundidade
        const profundidadeMaxCorte = 0.5;
        const numPasses = Math.max(1, Math.ceil(profundidade / profundidadeMaxCorte));
        const incremento = profundidade / numPasses;
        
        let movimentosCorte = 0;
        let movimentosRapidos = 0;
        
        // Para cada passe de profundidade
        for (let passe = 1; passe <= numPasses; passe++) {
            const zAtual = -(incremento * passe);
            gcode.push(`(Passe ${passe}/${numPasses} - Z: ${zAtual.toFixed(3)} mm)`);
            gcode.push(`F800 ; Velocidade de corte`);
            
            let emCorte = false;
            
            // Varredura em zig-zag
            for (let y = 0; y < alturaPx; y++) {
                // Alterna direção a cada linha (zig-zag)
                if (y % 2 === 0) {
                    // Linha par: esquerda → direita
                    for (let x = 0; x < larguraPx; x++) {
                        const idx = (y * larguraPx + x) * 4;
                        const r = pixels[idx];
                        const g = pixels[idx + 1];
                        const b = pixels[idx + 2];
                        const brilho = (r + g + b) / 3;
                        const deveCortar = brilho < limiar;
                        
                        if (deveCortar) {
                            const xMm = x * passoX;
                            const yMm = y * passoY;
                            
                            if (!emCorte) {
                                gcode.push(`G0 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                emCorte = true;
                                movimentosRapidos++;
                                movimentosCorte++;
                            } else {
                                gcode.push(`G1 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                movimentosCorte++;
                            }
                        } else if (emCorte) {
                            gcode.push(`G0 Z5.000`);
                            emCorte = false;
                            movimentosRapidos++;
                        }
                    }
                } else {
                    // Linha ímpar: direita → esquerda
                    for (let x = larguraPx - 1; x >= 0; x--) {
                        const idx = (y * larguraPx + x) * 4;
                        const r = pixels[idx];
                        const g = pixels[idx + 1];
                        const b = pixels[idx + 2];
                        const brilho = (r + g + b) / 3;
                        const deveCortar = brilho < limiar;
                        
                        if (deveCortar) {
                            const xMm = x * passoX;
                            const yMm = y * passoY;
                            
                            if (!emCorte) {
                                gcode.push(`G0 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                emCorte = true;
                                movimentosRapidos++;
                                movimentosCorte++;
                            } else {
                                gcode.push(`G1 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                movimentosCorte++;
                            }
                        } else if (emCorte) {
                            gcode.push(`G0 Z5.000`);
                            emCorte = false;
                            movimentosRapidos++;
                        }
                    }
                }
            }
            
            // Garante que a ferramenta está levantada no final do passe
            if (emCorte) {
                gcode.push(`G0 Z5.000`);
                movimentosRapidos++;
            }
        }
        
        gcode.push(``);
        gcode.push(`M5 ; Desliga spindle`);
        gcode.push(`G0 Z5.000 ; Sobe ferramenta`);
        gcode.push(`G0 X0 Y0 ; Retorna ao home`);
        gcode.push(`M30 ; Fim do programa`);
        
        return res.status(200).json({
            success: true,
            gcode: gcode.join('\n'),
            linhas: gcode.length,
            movimentos_corte: movimentosCorte,
            movimentos_rapidos: movimentosRapidos
        });
        
    } catch (error) {
        console.error('Erro:', error);
        return res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
}
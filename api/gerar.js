// api/gerar.js - API de processamento de imagem e geração de G-code

import sharp from 'sharp';

export default async function handler(req, res) {
    // CORS
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
            limiar = 128,
            qualidade = 'normal',
            passo_varredura = 0.5,
            otimizar_caminho = true
        } = req.body;
        
        if (!imagem) {
            return res.status(400).json({ success: false, error: 'Nenhuma imagem fornecida' });
        }
        
        // Ajusta resolução baseado na qualidade
        let resolucaoFinal = resolucao;
        if (qualidade === 'rapido') {
            resolucaoFinal = Math.max(1, Math.floor(resolucao / 2));
        } else if (qualidade === 'alto') {
            resolucaoFinal = Math.floor(resolucao * 1.5);
        }
        
        // Decodifica imagem
        const base64Data = imagem.split(',')[1];
        const imageBuffer = Buffer.from(base64Data, 'base64');
        
        // Calcula dimensões em pixels
        const larguraPx = Math.max(1, Math.floor(largura * resolucaoFinal));
        const alturaPx = Math.max(1, Math.floor(altura * resolucaoFinal));
        
        // Processa imagem com Sharp
        const processedImage = await sharp(imageBuffer)
            .resize(larguraPx, alturaPx, { fit: 'fill' })
            .grayscale()
            .raw()
            .toBuffer();
        
        const pixels = new Uint8Array(processedImage);
        
        // Calcula passo
        const passoX = largura / larguraPx;
        const passoY = altura / alturaPx;
        const passoVarreduraPx = Math.max(1, Math.floor(passo_varredura * resolucaoFinal));
        
        // Gera G-code
        const gcode = [];
        const dataHora = new Date().toLocaleString('pt-BR');
        
        gcode.push(`(CNC Pro - G-code Gerado a partir da Imagem)`);
        gcode.push(`(Data: ${dataHora})`);
        gcode.push(`(Dimensões: ${largura} x ${altura} mm)`);
        gcode.push(`(Profundidade: ${profundidade} mm)`);
        gcode.push(`(Resolução: ${resolucaoFinal} passos/mm)`);
        gcode.push(`(Limiar: ${limiar})`);
        gcode.push(`(Qualidade: ${qualidade})`);
        gcode.push(``);
        gcode.push(`G90 ; Coordenadas absolutas`);
        gcode.push(`G21 ; Unidades em mm`);
        gcode.push(`M3 S10000 ; Liga spindle`);
        gcode.push(`G0 Z5.000 ; Altura de segurança`);
        gcode.push(`G0 X0 Y0 ; Home`);
        gcode.push(``);
        
        // Passes de profundidade
        const profundidadeMaxCorte = 0.5;
        const numPasses = Math.max(1, Math.ceil(profundidade / profundidadeMaxCorte));
        const incremento = profundidade / numPasses;
        
        let movimentosCorte = 0;
        let movimentosRapidos = 0;
        let linhasGeradas = 0;
        
        for (let passe = 1; passe <= numPasses; passe++) {
            const zAtual = -(incremento * passe);
            gcode.push(`(Passe ${passe}/${numPasses} - Z: ${zAtual.toFixed(3)} mm)`);
            gcode.push(`F800 ; Velocidade de corte`);
            
            let emCorte = false;
            
            for (let y = 0; y < alturaPx; y++) {
                if (otimizar_caminho && y % passoVarreduraPx !== 0) continue;
                
                if (y % 2 === 0) {
                    for (let x = 0; x < larguraPx; x++) {
                        if (otimizar_caminho && x % passoVarreduraPx !== 0) continue;
                        
                        const idx = y * larguraPx + x;
                        const brilho = pixels[idx];
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
                                linhasGeradas += 2;
                            } else {
                                gcode.push(`G1 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                movimentosCorte++;
                                linhasGeradas++;
                            }
                        } else if (emCorte) {
                            gcode.push(`G0 Z5.000`);
                            emCorte = false;
                            movimentosRapidos++;
                            linhasGeradas++;
                        }
                    }
                } else {
                    for (let x = larguraPx - 1; x >= 0; x--) {
                        if (otimizar_caminho && x % passoVarreduraPx !== 0) continue;
                        
                        const idx = y * larguraPx + x;
                        const brilho = pixels[idx];
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
                                linhasGeradas += 2;
                            } else {
                                gcode.push(`G1 X${xMm.toFixed(3)} Y${yMm.toFixed(3)}`);
                                movimentosCorte++;
                                linhasGeradas++;
                            }
                        } else if (emCorte) {
                            gcode.push(`G0 Z5.000`);
                            emCorte = false;
                            movimentosRapidos++;
                            linhasGeradas++;
                        }
                    }
                }
            }
            
            if (emCorte) {
                gcode.push(`G0 Z5.000`);
                movimentosRapidos++;
                linhasGeradas++;
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
            movimentos_rapidos: movimentosRapidos,
            profundidade_max: profundidade,
            largura_px: larguraPx,
            altura_px: alturaPx,
            num_passes: numPasses
        });
        
    } catch (error) {
        console.error('Erro:', error);
        return res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
}
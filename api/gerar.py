// api/gerar.js - API em Node.js para o Vercel

const { createCanvas, loadImage } = require('canvas');

module.exports = async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    if (req.method !== 'POST') {
        return res.status(405).json({ success: false, error: 'Método não permitido' });
    }
    
    try {
        const { imagem, largura, altura, profundidade, resolucao, limiar } = req.body;
        
        if (!imagem) {
            return res.status(400).json({ success: false, error: 'Nenhuma imagem fornecida' });
        }
        
        // Decodifica a imagem base64
        const base64Data = imagem.split(',')[1];
        const imageBuffer = Buffer.from(base64Data, 'base64');
        
        // Carrega a imagem
        const img = await loadImage(imageBuffer);
        
        // Cria canvas para processamento
        const canvas = createCanvas(img.width, img.height);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        
        // Obtém dados da imagem
        const imageData = ctx.getImageData(0, 0, img.width, img.height);
        const data = imageData.data;
        
        // Calcula dimensões em pixels
        const passosPorMm = resolucao;
        const larguraPx = Math.max(1, Math.floor(largura * passosPorMm));
        const alturaPx = Math.max(1, Math.floor(altura * passosPorMm));
        
        // Redimensiona a imagem
        const resizedCanvas = createCanvas(larguraPx, alturaPx);
        const resizedCtx = resizedCanvas.getContext('2d');
        resizedCtx.drawImage(canvas, 0, 0, larguraPx, alturaPx);
        
        const resizedData = resizedCtx.getImageData(0, 0, larguraPx, alturaPx).data;
        
        // Gera G-code
        const gcode = [];
        gcode.push('(CNC Pro - G-code Gerado Online)');
        gcode.push(`(Dimensões: ${largura} x ${altura} mm)`);
        gcode.push(`(Profundidade: ${profundidade} mm)`);
        gcode.push(`(Resolução: ${resolucao} passos/mm)`);
        gcode.push('');
        gcode.push('G90 G21');
        gcode.push('M3 S10000');
        gcode.push('G0 Z5.000 F3500');
        gcode.push('G0 X0 Y0');
        gcode.push('');
        
        const passo = 1.0 / passosPorMm;
        const profundidadeCorte = 0.5;
        const numPasses = Math.max(1, Math.ceil(profundidade / profundidadeCorte));
        const incremento = profundidade / numPasses;
        
        let movimentosCorte = 0;
        let movimentosRapidos = 0;
        
        for (let p = 1; p <= numPasses; p++) {
            const z = -(incremento * p);
            gcode.push(`(Passe ${p}/${numPasses} Z: ${z.toFixed(3)} mm)`);
            gcode.push('F800');
            
            for (let y = 0; y < alturaPx; y++) {
                const xStart = y % 2 === 0 ? 0 : larguraPx - 1;
                const xEnd = y % 2 === 0 ? larguraPx : -1;
                const xStep = y % 2 === 0 ? 1 : -1;
                
                for (let x = xStart; x !== xEnd; x += xStep) {
                    const idx = (y * larguraPx + x) * 4;
                    const r = resizedData[idx];
                    const g = resizedData[idx + 1];
                    const b = resizedData[idx + 2];
                    const brilho = (r + g + b) / 3;
                    const cortar = brilho < limiar;
                    
                    if (cortar) {
                        const xMm = x * passo;
                        const yMm = y * passo;
                        gcode.push(`G1 X${xMm.toFixed(3)} Y${yMm.toFixed(3)} Z${z.toFixed(3)}`);
                        movimentosCorte++;
                    }
                }
            }
        }
        
        gcode.push('');
        gcode.push('M5');
        gcode.push('G0 Z5.000');
        gcode.push('G0 X0 Y0');
        gcode.push('M30');
        
        return res.status(200).json({
            success: true,
            gcode: gcode.join('\n'),
            linhas: gcode.length,
            movimentos_corte: movimentosCorte,
            movimentos_rapidos: movimentosRapidos
        });
        
    } catch (error) {
        console.error('Erro:', error);
        return res.status(500).json({ success: false, error: error.message });
    }
};

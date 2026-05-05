/**
 * CNC Pro - API de Geração de G-code
 * 
 * Esta API recebe uma imagem, processa seus pixels e gera código G-code
 * para usinagem CNC. Suporta diferentes estratégias de usinagem:
 * - pocket: Escavação completa da área escura
 * - profile: Apenas o contorno da imagem
 * - contour: Segue o perímetro
 * - zigzag: Varredura simples
 * 
 * @author CNC Pro
 * @version 2.0
 */

// Importa a biblioteca Sharp para processamento de imagens
import sharp from 'sharp';

/**
 * Handler principal da função serverless Vercel
 * @param {Object} req - Requisição HTTP
 * @param {Object} res - Resposta HTTP
 */
export default async function handler(req, res) {
    // ========== CONFIGURAÇÃO CORS ==========
    // Permite que qualquer origem acesse a API (necessário para frontend separado)
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    // ========== TRATAMENTO DE PREFLIGHT (OPTIONS) ==========
    // Navegadores enviam OPTIONS antes do POST para verificar CORS
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    
    // ========== VERIFICAÇÃO DO MÉTODO ==========
    // Apenas aceitamos requisições POST
    if (req.method !== 'POST') {
        return res.status(405).json({ 
            success: false, 
            error: 'Método não permitido. Use POST.' 
        });
    }
    
    try {
        // ========== EXTRAÇÃO DOS PARÂMETROS ==========
        const { 
            imagem,                    // Imagem em base64
            largura = 100,             // Largura da peça em mm
            altura = 100,              // Altura da peça em mm
            profundidade = 3,          // Profundidade total de corte em mm
            diametro = 3.175,          // Diâmetro da ferramenta em mm
            velocidade_corte = 800,    // Velocidade de corte em mm/min
            passo_corte = 0.5,         // Profundidade máxima por passe
            resolucao = 15,            // Passos por mm (qualidade)
            estrategia = 'pocket'      // Estratégia de usinagem
        } = req.body;
        
        // ========== VALIDAÇÃO DA IMAGEM ==========
        if (!imagem) {
            return res.status(400).json({ 
                success: false, 
                error: 'Nenhuma imagem fornecida' 
            });
        }
        
        // ========== PROCESSAMENTO DA IMAGEM ==========
        // Remove o cabeçalho base64 (ex: "data:image/png;base64,")
        const base64Data = imagem.split(',')[1];
        const imageBuffer = Buffer.from(base64Data, 'base64');
        
        // Calcula dimensões em pixels baseado na resolução
        const larguraPx = Math.max(1, Math.floor(largura * resolucao));
        const alturaPx = Math.max(1, Math.floor(altura * resolucao));
        
        // Processa a imagem com Sharp:
        // 1. Redimensiona para as dimensões de corte
        // 2. Converte para escala de cinza
        // 3. Extrai os pixels crus (0-255)
        const processedImage = await sharp(imageBuffer)
            .resize(larguraPx, alturaPx, { fit: 'fill' })
            .grayscale()
            .raw()
            .toBuffer();
        
        // Array de pixels (cada valor é brilho de 0=preto a 255=branco)
        const pixels = new Uint8Array(processedImage);
        
        // Calcula passo em mm por pixel
        const passoX = largura / larguraPx;
        const passoY = altura / alturaPx;
        
        // ========== GERAÇÃO DO G-CODE ==========
        const gcode = [];
        const dataHora = new Date().toLocaleString('pt-BR');
        
        // ---------- CABEÇALHO ----------
        gcode.push(`(CNC Pro - G-code Gerado Automaticamente)`);
        gcode.push(`(Data: ${dataHora})`);
        gcode.push(`(Dimensões: ${largura} x ${altura} mm)`);
        gcode.push(`(Profundidade: ${profundidade} mm)`);
        gcode.push(`(Ferramenta: ${diametro} mm)`);
        gcode.push(`(Resolução: ${resolucao} passos/mm)`);
        gcode.push(`(Estratégia: ${estrategia})`);
        gcode.push(`(Passo de corte: ${passo_corte} mm/passe)`);
        gcode.push(``);
        
        // Comandos iniciais do G-code
        gcode.push(`G90 ; Coordenadas absolutas`);
        gcode.push(`G21 ; Unidades em milímetros`);
        gcode.push(`M3 S10000 ; Liga o spindle`);
        gcode.push(`G0 Z5.000 ; Sobe para altura de segurança`);
        gcode.push(`G0 X0 Y0 ; Vai para origem`);
        gcode.push(``);
        
        // ========== CÁLCULO DOS PASSES DE PROFUNDIDADE ==========
        // Divide a profundidade total em passes para não sobrecarregar a ferramenta
        const numPasses = Math.ceil(profundidade / passo_corte);
        const incremento = profundidade / numPasses;
        
        let movimentosCorte = 0;
        let movimentosRapidos = 0;
        
        // ========== ESTRATÉGIA: ESCAVAÇÃO (POCKET) ==========
        // Ideal para: bolsos, áreas rebaixadas, gravação profunda
        // Preenche COMPLETAMENTE a área escura da imagem
        if (estrategia === 'pocket') {
            // Loop dos passes de profundidade
            for (let passe = 1; passe <= numPasses; passe++) {
                const zAtual = -(incremento * passe);
                gcode.push(`(Passe ${passe}/${numPasses} - Profundidade: ${zAtual.toFixed(3)} mm)`);
                gcode.push(`F${velocidade_corte} ; Velocidade de corte`);
                
                let emCorte = false;
                
                // Varredura em zig-zag para cada linha Y
                for (let y = 0; y < alturaPx; y++) {
                    const yPos = y * passoY;
                    
                    // Alterna direção a cada linha (otimiza movimentos)
                    if (y % 2 === 0) {
                        // Linha par: esquerda → direita
                        for (let x = 0; x < larguraPx; x++) {
                            const idx = y * larguraPx + x;
                            const brilho = pixels[idx];
                            const deveCortar = brilho < 128; // Escuro = cortar
                            
                            if (deveCortar) {
                                const xPos = x * passoX;
                                
                                if (!emCorte) {
                                    gcode.push(`G0 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                    emCorte = true;
                                    movimentosRapidos++;
                                    movimentosCorte++;
                                } else {
                                    gcode.push(`G1 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    movimentosCorte++;
                                }
                            } else if (emCorte) {
                                gcode.push(`G0 Z5.000`);
                                emCorte = false;
                                movimentosRapidos++;
                            }
                        }
                    } else {
                        // Linha ímpar: direita → esquerda (zig-zag)
                        for (let x = larguraPx - 1; x >= 0; x--) {
                            const idx = y * larguraPx + x;
                            const brilho = pixels[idx];
                            const deveCortar = brilho < 128;
                            
                            if (deveCortar) {
                                const xPos = x * passoX;
                                
                                if (!emCorte) {
                                    gcode.push(`G0 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                    emCorte = true;
                                    movimentosRapidos++;
                                    movimentosCorte++;
                                } else {
                                    gcode.push(`G1 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
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
                
                // Garantir que a ferramenta está levantada no final
                if (emCorte) {
                    gcode.push(`G0 Z5.000`);
                    movimentosRapidos++;
                }
                
                gcode.push(``);
            }
        }
        
        // ========== ESTRATÉGIA: PERFIL (PROFILE) ==========
        // Ideal para: recortes, peças, silhuetas
        // Segue APENAS o contorno da imagem
        else if (estrategia === 'profile') {
            // Encontra todos os pixels de borda
            const bordas = [];
            for (let y = 0; y < alturaPx; y++) {
                for (let x = 0; x < larguraPx; x++) {
                    const idx = y * larguraPx + x;
                    const brilho = pixels[idx];
                    
                    if (brilho < 128) {
                        // Verifica se é borda (tem pelo menos um vizinho branco)
                        const vizinhos = [
                            y > 0 && pixels[(y-1) * larguraPx + x] >= 128,
                            y < alturaPx-1 && pixels[(y+1) * larguraPx + x] >= 128,
                            x > 0 && pixels[y * larguraPx + (x-1)] >= 128,
                            x < larguraPx-1 && pixels[y * larguraPx + (x+1)] >= 128
                        ];
                        
                        if (vizinhos.some(v => v)) {
                            bordas.push({ x: x * passoX, y: y * passoY });
                        }
                    }
                }
            }
            
            // Ordena bordas para caminho contínuo (algoritmo simples)
            const caminho = [];
            const visitados = new Set();
            let atual = bordas[0];
            
            while (atual && caminho.length < bordas.length) {
                caminho.push(atual);
                const idx = `${atual.x},${atual.y}`;
                visitados.add(idx);
                
                // Encontra o ponto mais próximo não visitado
                let proximo = null;
                let menorDistancia = Infinity;
                
                for (const ponto of bordas) {
                    const pontoIdx = `${ponto.x},${ponto.y}`;
                    if (!visitados.has(pontoIdx)) {
                        const dist = Math.hypot(ponto.x - atual.x, ponto.y - atual.y);
                        if (dist < menorDistancia) {
                            menorDistancia = dist;
                            proximo = ponto;
                        }
                    }
                }
                atual = proximo;
            }
            
            // Gera os passes de profundidade para o contorno
            for (let passe = 1; passe <= numPasses; passe++) {
                const zAtual = -(incremento * passe);
                gcode.push(`(Passe ${passe}/${numPasses} - Profundidade: ${zAtual.toFixed(3)} mm)`);
                gcode.push(`F${velocidade_corte} ; Velocidade de corte`);
                
                if (caminho.length > 0) {
                    gcode.push(`G1 X${caminho[0].x.toFixed(3)} Y${caminho[0].y.toFixed(3)} Z${zAtual.toFixed(3)}`);
                    movimentosCorte++;
                    
                    for (let i = 1; i < caminho.length; i++) {
                        gcode.push(`G1 X${caminho[i].x.toFixed(3)} Y${caminho[i].y.toFixed(3)}`);
                        movimentosCorte++;
                    }
                }
                
                gcode.push(`G0 Z5.000`);
                movimentosRapidos++;
                gcode.push(``);
            }
        }
        
        // ========== ESTRATÉGIA: ZIG-ZAG SIMPLES ==========
        // Ideal para: texturas, acabamentos, desbaste
        else {
            for (let passe = 1; passe <= numPasses; passe++) {
                const zAtual = -(incremento * passe);
                gcode.push(`(Passe ${passe}/${numPasses} - Profundidade: ${zAtual.toFixed(3)} mm)`);
                gcode.push(`F${velocidade_corte} ; Velocidade de corte`);
                
                let emCorte = false;
                
                for (let y = 0; y < alturaPx; y++) {
                    const yPos = y * passoY;
                    
                    if (y % 2 === 0) {
                        for (let x = 0; x < larguraPx; x++) {
                            const idx = y * larguraPx + x;
                            const deveCortar = pixels[idx] < 128;
                            
                            if (deveCortar) {
                                const xPos = x * passoX;
                                
                                if (!emCorte) {
                                    gcode.push(`G0 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                    emCorte = true;
                                    movimentosRapidos++;
                                    movimentosCorte++;
                                } else {
                                    gcode.push(`G1 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    movimentosCorte++;
                                }
                            } else if (emCorte) {
                                gcode.push(`G0 Z5.000`);
                                emCorte = false;
                                movimentosRapidos++;
                            }
                        }
                    } else {
                        for (let x = larguraPx - 1; x >= 0; x--) {
                            const idx = y * larguraPx + x;
                            const deveCortar = pixels[idx] < 128;
                            
                            if (deveCortar) {
                                const xPos = x * passoX;
                                
                                if (!emCorte) {
                                    gcode.push(`G0 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
                                    gcode.push(`G1 Z${zAtual.toFixed(3)}`);
                                    emCorte = true;
                                    movimentosRapidos++;
                                    movimentosCorte++;
                                } else {
                                    gcode.push(`G1 X${xPos.toFixed(3)} Y${yPos.toFixed(3)}`);
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
                
                if (emCorte) {
                    gcode.push(`G0 Z5.000`);
                    movimentosRapidos++;
                }
                
                gcode.push(``);
            }
        }
        
        // ========== RODAPÉ ==========
        gcode.push(`M5 ; Desliga o spindle`);
        gcode.push(`G0 Z5.000 ; Sobe para altura de segurança`);
        gcode.push(`G0 X0 Y0 ; Retorna à origem`);
        gcode.push(`M30 ; Fim do programa`);
        
        // ========== RESPOSTA DE SUCESSO ==========
        return res.status(200).json({
            success: true,
            gcode: gcode.join('\n'),
            linhas: gcode.length,
            movimentos_corte: movimentosCorte,
            movimentos_rapidos: movimentosRapidos,
            profundidade_max: profundidade,
            num_passes: numPasses,
            dimensoes_px: { largura: larguraPx, altura: alturaPx }
        });
        
    } catch (error) {
        // ========== TRATAMENTO DE ERROS ==========
        console.error('Erro na API:', error);
        return res.status(500).json({ 
            success: false, 
            error: error.message 
        });
    }
}
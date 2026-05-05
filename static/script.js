/**
 * CNC Pro - Frontend JavaScript
 * Gerencia a interface do usuário, comunicação com a API e visualização 3D
 * 
 * @author CNC Pro
 * @version 2.0
 */

// ========== IMPORTAÇÕES ==========
import { GCodeViewer3D } from './viewer3d.js';

// ========== DOM ELEMENTS ==========
// Upload e imagem
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewContainer = document.getElementById('previewContainer');
const preview = document.getElementById('preview');
const removeImg = document.getElementById('removeImg');

// Botões principais
const gerarBtn = document.getElementById('gerarBtn');
const resetBtn = document.getElementById('resetBtn');
const baixarBtn = document.getElementById('baixarBtn');
const copiarBtn = document.getElementById('copiarBtn');
const toggleSidebar = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');

// Inputs de configuração
const larguraInput = document.getElementById('largura');
const alturaInput = document.getElementById('altura');
const profundidadeInput = document.getElementById('profundidade');
const diametroInput = document.getElementById('diametro');
const velocidadeCorteInput = document.getElementById('velocidadeCorte');
const passoCorteInput = document.getElementById('passoCorte');
const resolucaoInput = document.getElementById('resolucao');
const resolucaoValor = document.getElementById('resolucaoValor');
const limiarInput = document.getElementById('limiar');
const limiarValor = document.getElementById('limiarValor');

// Elementos de UI
const resultsContainer = document.getElementById('resultsContainer');
const gcodeOutput = document.getElementById('gcodeOutput');
const viewerPlaceholder = document.getElementById('viewerPlaceholder');

// ========== VARIÁVEIS GLOBAIS ==========
let currentImage = null;      // Imagem atual em base64
let currentGcode = null;      // G-code gerado atualmente
let viewer3D = null;          // Instância do visualizador 3D
let estrategiaAtual = 'pocket'; // Estratégia de usinagem atual

// ========== INICIALIZAÇÃO ==========
// Atualiza valores dos ranges
resolucaoInput.addEventListener('input', () => {
    resolucaoValor.textContent = resolucaoInput.value;
});

limiarInput.addEventListener('input', () => {
    limiarValor.textContent = limiarInput.value;
});

// Detecta mudança na estratégia
document.querySelectorAll('input[name="estrategia"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (e.target.checked) {
            estrategiaAtual = e.target.value;
            const nomes = {
                pocket: 'Escavação (Pocket)',
                profile: 'Perfil (Profile)',
                zigzag: 'Zig-Zag'
            };
            const modoAtual = document.getElementById('modoAtual');
            if (modoAtual) modoAtual.textContent = nomes[estrategiaAtual];
        }
    });
});

// Atualiza info da ferramenta
diametroInput.addEventListener('input', () => {
    const ferramentaInfo = document.getElementById('ferramentaInfo');
    if (ferramentaInfo) ferramentaInfo.textContent = `${diametroInput.value} mm`;
});

// Atualiza info de passes
function atualizarInfoPasses() {
    const profundidade = parseFloat(profundidadeInput.value);
    const passo = parseFloat(passoCorteInput.value);
    const passes = Math.ceil(profundidade / passo);
    const infoPasses = document.getElementById('infoPasses');
    if (infoPasses) infoPasses.textContent = `Serão feitos ${passes} passes de ${passo} mm cada`;
}

profundidadeInput.addEventListener('input', atualizarInfoPasses);
passoCorteInput.addEventListener('input', atualizarInfoPasses);
atualizarInfoPasses();

// ========== INICIALIZAÇÃO DO VISUALIZADOR 3D ==========
document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('canvas-container');
    if (container) {
        setTimeout(() => {
            try {
                viewer3D = new GCodeViewer3D('canvas-container');
                if (viewerPlaceholder) viewerPlaceholder.style.display = 'none';
                
                // Configura botões do visualizador
                const viewTop = document.getElementById('view-top');
                const viewFront = document.getElementById('view-front');
                const viewSide = document.getElementById('view-side');
                const viewIso = document.getElementById('view-iso');
                const resetView = document.getElementById('reset-view');
                
                if (viewTop) viewTop.addEventListener('click', () => viewer3D.setView('top'));
                if (viewFront) viewFront.addEventListener('click', () => viewer3D.setView('front'));
                if (viewSide) viewSide.addEventListener('click', () => viewer3D.setView('side'));
                if (viewIso) viewIso.addEventListener('click', () => viewer3D.setView('iso'));
                if (resetView) resetView.addEventListener('click', () => viewer3D.resetView());
            } catch (error) {
                console.error('Erro ao inicializar visualizador 3D:', error);
            }
        }, 200);
    }
});

// ========== SIDEBAR TOGGLE ==========
if (toggleSidebar) {
    toggleSidebar.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        toggleSidebar.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
        setTimeout(() => {
            if (viewer3D) viewer3D.onResize();
        }, 350);
    });
}

// ========== UPLOAD DE IMAGEM ==========
if (uploadArea) {
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => e.preventDefault());
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) handleImage(file);
    });
}

if (fileInput) {
    fileInput.addEventListener('change', (e) => {
        if (e.target.files[0]) handleImage(e.target.files[0]);
    });
}

if (removeImg) {
    removeImg.addEventListener('click', () => {
        currentImage = null;
        if (previewContainer) previewContainer.style.display = 'none';
        if (uploadArea) uploadArea.style.display = 'block';
        if (viewer3D) viewer3D.clear();
        if (resultsContainer) resultsContainer.style.display = 'none';
        currentGcode = null;
    });
}

function handleImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImage = e.target.result;
        if (preview) preview.src = currentImage;
        if (previewContainer) previewContainer.style.display = 'block';
        if (uploadArea) uploadArea.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// ========== RESETAR CONFIGURAÇÕES ==========
if (resetBtn) {
    resetBtn.addEventListener('click', () => {
        // Reset dos inputs
        if (larguraInput) larguraInput.value = '100';
        if (alturaInput) alturaInput.value = '100';
        if (profundidadeInput) profundidadeInput.value = '3';
        if (diametroInput) diametroInput.value = '3.175';
        if (velocidadeCorteInput) velocidadeCorteInput.value = '800';
        if (passoCorteInput) passoCorteInput.value = '0.5';
        if (resolucaoInput) {
            resolucaoInput.value = '15';
            resolucaoValor.textContent = '15';
        }
        if (limiarInput) {
            limiarInput.value = '128';
            limiarValor.textContent = '128';
        }
        
        // Reset da estratégia
        const pocketRadio = document.querySelector('input[value="pocket"]');
        if (pocketRadio) pocketRadio.checked = true;
        estrategiaAtual = 'pocket';
        const modoAtual = document.getElementById('modoAtual');
        if (modoAtual) modoAtual.textContent = 'Escavação (Pocket)';
        const ferramentaInfo = document.getElementById('ferramentaInfo');
        if (ferramentaInfo) ferramentaInfo.textContent = '3.175 mm';
        
        // Reset da imagem
        currentImage = null;
        if (previewContainer) previewContainer.style.display = 'none';
        if (uploadArea) uploadArea.style.display = 'block';
        
        // Reset dos resultados
        currentGcode = null;
        if (resultsContainer) resultsContainer.style.display = 'none';
        if (viewer3D) viewer3D.clear();
        
        atualizarInfoPasses();
    });
}

// ========== GERAR G-CODE ==========
if (gerarBtn) {
    gerarBtn.addEventListener('click', async () => {
        if (!currentImage) {
            alert('❌ Selecione uma imagem primeiro!');
            return;
        }
        
        gerarBtn.disabled = true;
        gerarBtn.textContent = '🔄 Processando...';
        
        const data = {
            imagem: currentImage,
            largura: parseFloat(larguraInput.value),
            altura: parseFloat(alturaInput.value),
            profundidade: parseFloat(profundidadeInput.value),
            diametro: parseFloat(diametroInput.value),
            velocidade_corte: parseFloat(velocidadeCorteInput.value),
            passo_corte: parseFloat(passoCorteInput.value),
            resolucao: parseFloat(resolucaoInput.value),
            limiar: parseInt(limiarInput.value),
            estrategia: estrategiaAtual
        };
        
        try {
            const response = await fetch('/api/gerar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                currentGcode = result.gcode;
                
                // ========== EXIBE O G-CODE ==========
                if (gcodeOutput) {
                    gcodeOutput.innerHTML = `<pre style="margin:0; white-space:pre-wrap; font-family:'Courier New',monospace; font-size:11px; line-height:1.4;">${escapeHtml(result.gcode)}</pre>`;
                }
                
                // ========== ATUALIZA ESTATÍSTICAS ==========
                const totalLinhas = document.getElementById('totalLinhas');
                const movimentosCorte = document.getElementById('movimentosCorte');
                const tempoEstimado = document.getElementById('tempoEstimado');
                
                if (totalLinhas) totalLinhas.textContent = result.linhas.toLocaleString();
                if (movimentosCorte) movimentosCorte.textContent = result.movimentos_corte.toLocaleString();
                
                // Calcula tempo estimado (baseado em 800mm/min)
                const tempo = Math.ceil(result.movimentos_corte / 800);
                if (tempoEstimado) tempoEstimado.textContent = tempo;
                
                // ========== MOSTRA O CONTAINER DE RESULTADOS ==========
                if (resultsContainer) resultsContainer.style.display = 'flex';
                
                // ========== CARREGA NO VISUALIZADOR 3D ==========
                if (viewer3D && currentGcode) {
                    viewer3D.clear();
                    viewer3D.loadGCode(currentGcode);
                    if (viewerPlaceholder) viewerPlaceholder.style.display = 'none';
                }
                
                // ========== HABILITA BOTÕES ==========
                if (baixarBtn) baixarBtn.disabled = false;
                if (copiarBtn) copiarBtn.disabled = false;
                
            } else {
                alert('❌ Erro: ' + (result.error || 'Falha ao gerar G-code'));
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('❌ Erro ao conectar com o servidor: ' + error.message);
        } finally {
            gerarBtn.disabled = false;
            gerarBtn.textContent = '🚀 GERAR G-CODE';
        }
    });
}

// ========== BAIXAR G-CODE ==========
if (baixarBtn) {
    baixarBtn.addEventListener('click', () => {
        if (!currentGcode) return;
        
        const blob = new Blob([currentGcode], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cnc_pro_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.nc`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });
}

// ========== COPIAR G-CODE ==========
if (copiarBtn) {
    copiarBtn.addEventListener('click', async () => {
        if (!currentGcode) return;
        
        try {
            await navigator.clipboard.writeText(currentGcode);
            alert('✅ G-code copiado para a área de transferência!');
        } catch (err) {
            alert('❌ Erro ao copiar: ' + err.message);
        }
    });
}

// ========== UTILITÁRIOS ==========
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== VALORES INICIAIS ==========
atualizarInfoPasses();
const ferramentaInfo = document.getElementById('ferramentaInfo');
if (ferramentaInfo) ferramentaInfo.textContent = '3.175 mm';
const modoAtual = document.getElementById('modoAtual');
if (modoAtual) modoAtual.textContent = 'Escavação (Pocket)';
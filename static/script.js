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
            document.getElementById('modoAtual').textContent = nomes[estrategiaAtual];
        }
    });
});

// Atualiza info da ferramenta
diametroInput.addEventListener('input', () => {
    document.getElementById('ferramentaInfo').textContent = `${diametroInput.value} mm`;
});

// Atualiza info de passes
function atualizarInfoPasses() {
    const profundidade = parseFloat(profundidadeInput.value);
    const passo = parseFloat(passoCorteInput.value);
    const passes = Math.ceil(profundidade / passo);
    document.getElementById('infoPasses').textContent = `Serão feitos ${passes} passes de ${passo} mm cada`;
}

profundidadeInput.addEventListener('input', atualizarInfoPasses);
passoCorteInput.addEventListener('input', atualizarInfoPasses);
atualizarInfoPasses();

// ========== INICIALIZAÇÃO DO VISUALIZADOR 3D ==========
setTimeout(() => {
    const container = document.getElementById('canvas-container');
    if (container) {
        viewer3D = new GCodeViewer3D('canvas-container');
        if (viewerPlaceholder) viewerPlaceholder.style.display = 'none';
        
        // Configura botões do visualizador
        document.getElementById('view-top')?.addEventListener('click', () => viewer3D.setView('top'));
        document.getElementById('view-front')?.addEventListener('click', () => viewer3D.setView('front'));
        document.getElementById('view-side')?.addEventListener('click', () => viewer3D.setView('side'));
        document.getElementById('view-iso')?.addEventListener('click', () => viewer3D.setView('iso'));
        document.getElementById('reset-view')?.addEventListener('click', () => viewer3D.resetView());
    }
}, 100);

// ========== SIDEBAR TOGGLE ==========
toggleSidebar?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    toggleSidebar.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
    setTimeout(() => viewer3D?.onResize(), 300);
});

// ========== UPLOAD DE IMAGEM ==========
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => e.preventDefault());
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file?.type.startsWith('image/')) handleImage(file);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleImage(e.target.files[0]);
});

removeImg?.addEventListener('click', () => {
    currentImage = null;
    previewContainer.style.display = 'none';
    uploadArea.style.display = 'block';
    if (viewer3D) viewer3D.clear();
    resultsContainer.style.display = 'none';
});

function handleImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImage = e.target.result;
        preview.src = currentImage;
        previewContainer.style.display = 'block';
        uploadArea.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// ========== RESETAR CONFIGURAÇÕES ==========
resetBtn?.addEventListener('click', () => {
    // Reset dos inputs
    larguraInput.value = '100';
    alturaInput.value = '100';
    profundidadeInput.value = '3';
    diametroInput.value = '3.175';
    velocidadeCorteInput.value = '800';
    passoCorteInput.value = '0.5';
    resolucaoInput.value = '15';
    resolucaoValor.textContent = '15';
    limiarInput.value = '128';
    limiarValor.textContent = '128';
    
    // Reset da estratégia
    document.querySelector('input[value="pocket"]').checked = true;
    estrategiaAtual = 'pocket';
    document.getElementById('modoAtual').textContent = 'Escavação (Pocket)';
    document.getElementById('ferramentaInfo').textContent = '3.175 mm';
    
    // Reset da imagem
    currentImage = null;
    previewContainer.style.display = 'none';
    uploadArea.style.display = 'block';
    
    // Reset dos resultados
    currentGcode = null;
    resultsContainer.style.display = 'none';
    if (viewer3D) viewer3D.clear();
    
    atualizarInfoPasses();
});

// ========== GERAR G-CODE ==========
gerarBtn?.addEventListener('click', async () => {
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
            
            // Exibe o G-code
            gcodeOutput.innerHTML = `<pre style="margin:0; white-space:pre-wrap; font-family:monospace; font-size:11px;">${escapeHtml(result.gcode)}</pre>`;
            
            // Atualiza estatísticas
            document.getElementById
// static/script.js - Lógica com foco em usinagem real

import { GCodeViewer3D } from './viewer3d.js';

// Elementos
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const previewContainer = document.getElementById('previewContainer');
const preview = document.getElementById('preview');
const removeImg = document.getElementById('removeImg');
const gerarBtn = document.getElementById('gerarBtn');
const resetBtn = document.getElementById('resetBtn');
const baixarBtn = document.getElementById('baixarBtn');
const copiarBtn = document.getElementById('copiarBtn');
const toggleSidebar = document.getElementById('toggleSidebar');
const sidebar = document.getElementById('sidebar');
const resultsContainer = document.getElementById('resultsContainer');
const gcodeOutput = document.getElementById('gcodeOutput');

// Inputs
const larguraInput = document.getElementById('largura');
const alturaInput = document.getElementById('altura');
const profundidadeInput = document.getElementById('profundidade');
const diametroInput = document.getElementById('diametro');
const velocidadeCorteInput = document.getElementById('velocidadeCorte');
const passoCorteInput = document.getElementById('passoCorte');
const resolucaoInput = document.getElementById('resolucao');
const resolucaoValor = document.getElementById('resolucaoValor');

let currentImage = null;
let currentGcode = null;
let viewer3D = null;
let estrategiaAtual = 'pocket';

// Inicializa visualizador
setTimeout(() => {
    const container = document.getElementById('canvas-container');
    if (container) {
        viewer3D = new GCodeViewer3D('canvas-container');
        document.getElementById('viewerPlaceholder')?.remove();
        
        // Botões do visualizador
        document.getElementById('view-top')?.addEventListener('click', () => viewer3D.setView('top'));
        document.getElementById('view-front')?.addEventListener('click', () => viewer3D.setView('front'));
        document.getElementById('view-side')?.addEventListener('click', () => viewer3D.setView('side'));
        document.getElementById('view-iso')?.addEventListener('click', () => viewer3D.setView('iso'));
        document.getElementById('reset-view')?.addEventListener('click', () => viewer3D.resetView());
        document.getElementById('toggleGrid')?.addEventListener('click', () => viewer3D.toggleGrid());
    }
}, 100);

// Sidebar toggle
toggleSidebar?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    toggleSidebar.textContent = sidebar.classList.contains('collapsed') ? '▶' : '◀';
    setTimeout(() => viewer3D?.onResize(), 300);
});

// Upload
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

// Resolução range
resolucaoInput?.addEventListener('input', () => {
    resolucaoValor.textContent = resolucaoInput.value;
});

// Passo de corte
passoCorteInput?.addEventListener('input', () => {
    const profundidade = parseFloat(profundidadeInput.value);
    const passo = parseFloat(passoCorteInput.value);
    const passes = Math.ceil(profundidade / passo);
    document.getElementById('infoPasses').textContent = `Serão feitos ${passes} passes`;
});

// Estratégia
document.querySelectorAll('input[name="estrategia"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (e.target.checked) {
            estrategiaAtual = e.target.value;
            const nomes = {
                pocket: 'Escavação (Pocket)',
                profile: 'Perfil (Profile)',
                contour: 'Contorno',
                zigzag: 'Zig-Zag'
            };
            document.getElementById('modoAtual').textContent = nomes[estrategiaAtual];
        }
    });
});

// Ferramenta info
diametroInput?.addEventListener('input', () => {
    document.getElementById('ferramentaInfo').textContent = `${diametroInput.value} mm`;
});

// Reset
resetBtn?.addEventListener('click', () => {
    larguraInput.value = '100';
    alturaInput.value = '100';
    profundidadeInput.value = '3';
    diametroInput.value = '3.175';
    velocidadeCorteInput.value = '800';
    passoCorteInput.value = '0.5';
    resolucaoInput.value = '15';
    resolucaoValor.textContent = '15';
    document.querySelector('input[value="pocket"]').checked = true;
    estrategiaAtual = 'pocket';
    document.getElementById('modoAtual').textContent = 'Escavação (Pocket)';
    document.getElementById('ferramentaInfo').textContent = '3.175 mm';
    currentImage = null;
    previewContainer.style.display = 'none';
    uploadArea.style.display = 'block';
    currentGcode = null;
    resultsContainer.style.display = 'none';
    if (viewer3D) viewer3D.clear();
});

// Gerar G-code
gerarBtn?.addEventListener('click', async () => {
    if (!currentImage) {
        alert('Selecione uma imagem primeiro!');
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
            gcodeOutput.innerHTML = `<pre style="margin:0">${escapeHtml(result.gcode)}</pre>`;
            
            document.getElementById('totalLinhas').textContent = result.linhas.toLocaleString();
            document.getElementById('movimentosCorte').textContent = result.movimentos_corte.toLocaleString();
            
            const tempo = Math.ceil(result.movimentos_corte / 800 * 0.1);
            document.getElementById('tempoEstimado').textContent = tempo;
            
            resultsContainer.style.display = 'flex';
            
            if (viewer3D && currentGcode) {
                viewer3D.loadGCode(currentGcode);
            }
            
            baixarBtn.disabled = false;
            copiarBtn.disabled = false;
        } else {
            alert('Erro: ' + result.error);
        }
    } catch (error) {
        alert('Erro: ' + error.message);
    } finally {
        gerarBtn.disabled = false;
        gerarBtn.textContent = '🚀 GERAR G-CODE';
    }
});

// Baixar
baixarBtn?.addEventListener('click', () => {
    if (!currentGcode) return;
    const blob = new Blob([currentGcode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'projeto_cnc.nc';
    a.click();
    URL.revokeObjectURL(url);
});

// Copiar
copiarBtn?.addEventListener('click', async () => {
    if (!currentGcode) return;
    await navigator.clipboard.writeText(currentGcode);
    alert('G-code copiado!');
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Atualiza info de passes
passoCorteInput.dispatchEvent(new Event('input'));
profundidadeInput.addEventListener('input', () => passoCorteInput.dispatchEvent(new Event('input')));
diametroInput.dispatchEvent(new Event('input'));
// static/script.js - Lógica principal com integração 3D

// Elementos do DOM
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const preview = document.getElementById('preview');
const gerarBtn = document.getElementById('gerarBtn');
const baixarBtn = document.getElementById('baixarBtn');
const copiarBtn = document.getElementById('copiarBtn');
const gcodeOutput = document.getElementById('gcodeOutput');
const progressBar = document.getElementById('progressBar');
const progressFill = document.getElementById('progressFill');
const statsDiv = document.getElementById('stats');
const resolucao = document.getElementById('resolucao');
const resolucaoValor = document.getElementById('resolucaoValor');
const limiar = document.getElementById('limiar');
const limiarValor = document.getElementById('limiarValor');

let currentImage = null;
let currentGcode = null;
let viewer3D = null;

// Inicializa visualizador 3D quando o módulo carregar
import('./viewer3d.js').then(module => {
    const container = document.getElementById('canvas-container');
    if (container && module.GCodeViewer3D) {
        viewer3D = new module.GCodeViewer3D('canvas-container');
        
        // Configura botões do visualizador
        document.getElementById('view-top')?.addEventListener('click', () => viewer3D.setView('top'));
        document.getElementById('view-front')?.addEventListener('click', () => viewer3D.setView('front'));
        document.getElementById('view-side')?.addEventListener('click', () => viewer3D.setView('side'));
        document.getElementById('view-iso')?.addEventListener('click', () => viewer3D.setView('iso'));
        document.getElementById('reset-view')?.addEventListener('click', () => viewer3D.resetView());
    }
});

// Atualiza valores dos ranges
resolucao.addEventListener('input', () => {
    resolucaoValor.textContent = resolucao.value;
});

limiar.addEventListener('input', () => {
    limiarValor.textContent = limiar.value;
});

// Upload area
uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleImage(file);
    }
});
fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleImage(e.target.files[0]);
});

// Abas
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(`tab-${tabId}`).classList.add('active');
        
        // Atualiza tamanho do visualizador 3D quando a aba é ativada
        if (tabId === 'viewer3d' && viewer3D) {
            setTimeout(() => viewer3D.onResize(), 100);
        }
    });
});

function handleImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImage = e.target.result;
        preview.src = currentImage;
        preview.style.display = 'block';
        uploadArea.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

// Gerar G-code
gerarBtn.addEventListener('click', async () => {
    if (!currentImage) {
        alert('Selecione uma imagem primeiro!');
        return;
    }
    
    gerarBtn.disabled = true;
    progressBar.style.display = 'block';
    progressFill.style.width = '30%';
    
    const data = {
        imagem: currentImage,
        largura: parseFloat(document.getElementById('largura').value),
        altura: parseFloat(document.getElementById('altura').value),
        profundidade: parseFloat(document.getElementById('profundidade').value),
        resolucao: parseFloat(resolucao.value),
        limiar: parseInt(limiar.value),
        qualidade: document.getElementById('qualidade').value,
        passo_varredura: parseFloat(document.getElementById('passoVarredura').value),
        otimizar_caminho: document.getElementById('otimizarCaminho').checked
    };
    
    try {
        progressFill.style.width = '60%';
        
        const response = await fetch('/api/gerar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        progressFill.style.width = '90%';
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const result = await response.json();
        
        if (result.success) {
            progressFill.style.width = '100%';
            currentGcode = result.gcode;
            
            // Exibe G-code
            gcodeOutput.innerHTML = `<pre style="margin: 0; white-space: pre-wrap;">${escapeHtml(result.gcode)}</pre>`;
            
            // Atualiza estatísticas
            document.getElementById('totalLinhas').textContent = result.linhas.toLocaleString();
            document.getElementById('movimentosCorte').textContent = result.movimentos_corte.toLocaleString();
            document.getElementById('movimentosRapidos').textContent = result.movimentos_rapidos.toLocaleString();
            document.getElementById('profundidadeMax').textContent = `${result.profundidade_max} mm`;
            document.getElementById('numPasses').textContent = result.num_passes;
            document.getElementById('resolucaoFinal').textContent = `${result.largura_px} x ${result.altura_px} px`;
            statsDiv.style.display = 'grid';
            
            // Carrega no visualizador 3D
            if (viewer3D && currentGcode) {
                viewer3D.loadGCode(currentGcode);
            }
            
            baixarBtn.disabled = false;
            copiarBtn.disabled = false;
            
            setTimeout(() => {
                progressBar.style.display = 'none';
                progressFill.style.width = '0%';
            }, 1000);
            
        } else {
            throw new Error(result.error || 'Erro desconhecido');
        }
        
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao gerar G-code: ' + error.message);
        progressBar.style.display = 'none';
        progressFill.style.width = '0%';
    } finally {
        gerarBtn.disabled = false;
    }
});

// Baixar G-code
baixarBtn.addEventListener('click', () => {
    if (!currentGcode) return;
    const blob = new Blob([currentGcode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'projeto_cnc.nc';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// Copiar G-code
copiarBtn.addEventListener('click', async () => {
    if (!currentGcode) return;
    try {
        await navigator.clipboard.writeText(currentGcode);
        alert('G-code copiado para a área de transferência!');
    } catch (err) {
        alert('Erro ao copiar: ' + err.message);
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
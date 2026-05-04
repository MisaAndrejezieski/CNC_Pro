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
const limiar = document.getElementById('limiar');
const limiarValue = document.getElementById('limiarValue');

let currentImage = null;
let currentGcode = null;

// Atualiza valor do limiar
limiar.addEventListener('input', () => {
    limiarValue.textContent = limiar.value;
});

// Upload area - clique
uploadArea.addEventListener('click', () => fileInput.click());

// Upload area - drag & drop
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

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
        handleImage(e.target.files[0]);
    }
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
        largura: document.getElementById('largura').value,
        altura: document.getElementById('altura').value,
        profundidade: document.getElementById('profundidade').value,
        resolucao: document.getElementById('resolucao').value,
        limiar: limiar.value
    };
    
    try {
        progressFill.style.width = '60%';
        
        const response = await fetch('/api/gerar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        progressFill.style.width = '90%';
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            progressFill.style.width = '100%';
            currentGcode = result.gcode;
            
            // Exibe G-code
            gcodeOutput.innerHTML = `<pre style="margin: 0; white-space: pre-wrap;">${escapeHtml(result.gcode)}</pre>`;
            
            // Atualiza estatísticas
            document.getElementById('totalLinhas').textContent = result.linhas;
            document.getElementById('movimentosCorte').textContent = result.movimentos_corte;
            document.getElementById('movimentosRapidos').textContent = result.movimentos_rapidos;
            statsDiv.style.display = 'grid';
            
            // Habilita botões
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

// Helper para escapar HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
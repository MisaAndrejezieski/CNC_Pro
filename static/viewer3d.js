/**
 * CNC Pro - Visualizador 3D de G-code
 * 
 * Utiliza Three.js para renderizar a trajetória da ferramenta CNC
 * Suporta:
 * - Visualização 3D interativa (rotação, zoom, pan)
 * - Cores diferentes para movimentos de corte e rápidos
 * - Pontos especiais (início, fim, profundidade máxima)
 * - Vistas predefinidas (topo, frente, lado, isométrico)
 * - Grid e eixos de referência
 * 
 * @author CNC Pro
 * @version 2.0
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';

export class GCodeViewer3D {
    /**
     * Construtor do visualizador 3D
     * @param {string} containerId - ID do elemento DOM que vai conter o canvas
     */
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Container não encontrado:', containerId);
            return;
        }
        
        this.scene = null;           // Cena Three.js
        this.camera = null;          // Câmera
        this.renderer = null;        // Renderizador WebGL
        this.labelRenderer = null;    // Renderizador para textos
        this.controls = null;         // Controles de órbita
        this.lines = [];              // Linhas renderizadas
        this.spheres = [];            // Esferas especiais
        
        this.init();
    }
    
    /**
     * Inicializa a cena 3D
     */
    init() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        // ========== CENA ==========
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a0f);
        this.scene.fog = new THREE.FogExp2(0x0a0a0f, 0.0005);
        
        // ========== CÂMERA ==========
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        this.camera.position.set(150, 150, 150);
        this.camera.lookAt(0, 0, 0);
        
        // ========== RENDERIZADOR PRINCIPAL ==========
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);
        
        // ========== RENDERIZADOR DE TEXTOS (CSS2D) ==========
        this.labelRenderer = new CSS2DRenderer();
        this.labelRenderer.setSize(width, height);
        this.labelRenderer.domElement.style.position = 'absolute';
        this.labelRenderer.domElement.style.top = '0px';
        this.labelRenderer.domElement.style.left = '0px';
        this.labelRenderer.domElement.style.pointerEvents = 'none';
        this.container.appendChild(this.labelRenderer.domElement);
        
        // ========== CONTROLES DE ÓRBITA ==========
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;      // Inércia
        this.controls.dampingFactor = 0.05;
        this.controls.rotateSpeed = 1.0;
        this.controls.zoomSpeed = 1.2;
        this.controls.panSpeed = 0.8;
        this.controls.enableZoom = true;
        this.controls.enablePan = true;
        
        // ========== ILUMINAÇÃO ==========
        this.addLights();
        
        // ========== REFERÊNCIAS VISUAIS ==========
        this.addGrid();
        this.addAxes();
        
        // ========== OBSERVADOR DE REDIMENSIONAMENTO ==========
        const resizeObserver = new ResizeObserver(() => this.onResize());
        resizeObserver.observe(this.container);
        
        // ========== INICIA ANIMAÇÃO ==========
        this.animate();
    }
    
    /**
     * Adiciona iluminação à cena
     */
    addLights() {
        // Luz ambiente - iluminação geral
        const ambientLight = new THREE.AmbientLight(0x404060);
        this.scene.add(ambientLight);
        
        // Luz direcional principal - cria sombras e volume
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(50, 100, 50);
        directionalLight.castShadow = true;
        directionalLight.receiveShadow = true;
        this.scene.add(directionalLight);
        
        // Luz de preenchimento - suaviza sombras
        const fillLight = new THREE.PointLight(0x4466cc, 0.3);
        fillLight.position.set(-30, 20, 30);
        this.scene.add(fillLight);
        
        // Luz traseira - realça bordas
        const backLight = new THREE.PointLight(0xffaa44, 0.2);
        backLight.position.set(0, 30, -50);
        this.scene.add(backLight);
    }
    
    /**
     * Adiciona grid de referência
     */
    addGrid() {
        // Grid principal (linhas a cada 10mm)
        const gridHelper = new THREE.GridHelper(200, 20, 0x4488aa, 0x335566);
        gridHelper.position.y = -0.1;
        gridHelper.material.transparent = true;
        gridHelper.material.opacity = 0.5;
        this.scene.add(gridHelper);
        
        // Grid fino (linhas a cada 2mm)
        const fineGrid = new THREE.GridHelper(200, 100, 0x336677, 0x224455);
        fineGrid.position.y = -0.05;
        fineGrid.material.transparent = true;
        fineGrid.material.opacity = 0.3;
        this.scene.add(fineGrid);
    }
    
    /**
     * Adiciona eixos X, Y, Z com setas e labels
     */
    addAxes() {
        // Eixo X (vermelho)
        const xAxis = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), 50, 0xff3333, 5, 3);
        this.scene.add(xAxis);
        
        // Eixo Y (verde)
        const yAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 50, 0x33ff33, 5, 3);
        this.scene.add(yAxis);
        
        // Eixo Z (azul)
        const zAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), 50, 0x3399ff, 5, 3);
        this.scene.add(zAxis);
        
        // Labels dos eixos
        const makeLabel = (text, color, position) => {
            const div = document.createElement('div');
            div.textContent = text;
            div.style.color = color;
            div.style.fontSize = '16px';
            div.style.fontWeight = 'bold';
            div.style.textShadow = '1px 1px 0px black';
            div.style.fontFamily = 'monospace';
            const label = new CSS2DObject(div);
            label.position.copy(position);
            this.scene.add(label);
        };
        
        makeLabel('X', '#ff6666', new THREE.Vector3(55, -5, -5));
        makeLabel('Y', '#66ff66', new THREE.Vector3(-5, 55, -5));
        makeLabel('Z', '#66aaff', new THREE.Vector3(-5, -5, 55));
    }
    
    /**
     * Carrega e renderiza um G-code
     * @param {string} gcode - String com o código G-code
     */
    loadGCode(gcode) {
        // Limpa renderizações anteriores
        this.clear();
        
        // Parse do G-code
        const pontos = this.parseGCode(gcode);
        if (pontos.length === 0) {
            console.warn('Nenhum movimento encontrado no G-code');
            return;
        }
        
        // Materiais para os diferentes tipos de movimento
        const materialCorte = new THREE.LineBasicMaterial({ color: 0x00ff88, linewidth: 2 });
        const materialRapido = new THREE.LineBasicMaterial({ color: 0x888888, linewidth: 1 });
        
        // Desenha cada segmento contínuo
        let segmentoAtual = [];
        let tipoAtual = null;
        
        for (let i = 0; i < pontos.length; i++) {
            const p = pontos[i];
            
            // Quando muda o tipo de movimento, desenha o segmento anterior
            if (tipoAtual !== p.tipo && segmentoAtual.length > 1) {
                this.drawSegment(segmentoAtual, tipoAtual === 'corte' ? materialCorte : materialRapido);
                segmentoAtual = [];
            }
            
            // Adiciona ponto ao segmento atual (convertendo coordenadas: Three.js usa Y como altura, então Y ↔ Z)
            segmentoAtual.push(new THREE.Vector3(p.x, p.z, p.y));
            tipoAtual = p.tipo;
        }
        
        // Desenha o último segmento
        if (segmentoAtual.length > 1) {
            this.drawSegment(segmentoAtual, tipoAtual === 'corte' ? materialCorte : materialRapido);
        }
        
        // Adiciona pontos especiais (início, fim, profundidade máxima)
        this.addSpecialPoints(pontos);
        
        // Ajusta a câmera para ver toda a trajetória
        this.fitToView(pontos);
    }
    
    /**
     * Desenha um segmento de linha contínuo
     * @param {Array} pontos - Array de pontos Vector3
     * @param {THREE.Material} material - Material da linha
     */
    drawSegment(pontos, material) {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        
        pontos.forEach(p => {
            vertices.push(p.x, p.y, p.z);
        });
        
        geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vertices), 3));
        const line = new THREE.Line(geometry, material);
        this.scene.add(line);
        this.lines.push(line);
    }
    
    /**
     * Adiciona pontos especiais (início, fim, profundidade máxima)
     * @param {Array} pontos - Array de pontos do G-code
     */
    addSpecialPoints(pontos) {
        if (pontos.length === 0) return;
        
        // Ponto INÍCIO (verde brilhante)
        const startPoint = pontos[0];
        const startSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.8, 32, 32),
            new THREE.MeshStandardMaterial({ color: 0x33ff33, emissive: 0x116611 })
        );
        startSphere.position.set(startPoint.x, startPoint.z, startPoint.y);
        this.scene.add(startSphere);
        this.spheres.push(startSphere);
        
        // Ponto FIM (vermelho)
        const endPoint = pontos[pontos.length - 1];
        const endSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.8, 32, 32),
            new THREE.MeshStandardMaterial({ color: 0xff3333, emissive: 0x661111 })
        );
        endSphere.position.set(endPoint.x, endPoint.z, endPoint.y);
        this.scene.add(endSphere);
        this.spheres.push(endSphere);
        
        // Ponto de PROFUNDIDADE MÁXIMA (laranja)
        let maxDepth = 0;
        let deepestPoint = null;
        pontos.forEach(p => {
            if (p.z < maxDepth) {
                maxDepth = p.z;
                deepestPoint = p;
            }
        });
        
        if (deepestPoint && maxDepth < -0.5) {
            const depthSphere = new THREE.Mesh(
                new THREE.SphereGeometry(1.5, 32, 32),
                new THREE.MeshStandardMaterial({ color: 0xff6600, emissive: 0x442200 })
            );
            depthSphere.position.set(deepestPoint.x, deepestPoint.z, deepestPoint.y);
            this.scene.add(depthSphere);
            this.spheres.push(depthSphere);
        }
    }
    
    /**
     * Analisa o G-code e extrai coordenadas e tipos de movimento
     * @param {string} gcode - String do G-code
     * @returns {Array} Array de pontos {x, y, z, tipo}
     */
    parseGCode(gcode) {
        const linhas = gcode.split('\n');
        const pontos = [];
        let x = 0, y = 0, z = 0;
        let tipoAtual = 'rapido';
        
        for (const linha of linhas) {
            const linhaUpper = linha.toUpperCase();
            
            // Determina tipo de movimento baseado no comando G
            if (linhaUpper.startsWith('G0')) {
                tipoAtual = 'rapido';
            } else if (linhaUpper.startsWith('G1')) {
                tipoAtual = 'corte';
            } else {
                continue; // Ignora outros comandos
            }
            
            // Extrai coordenadas
            const xMatch = linhaUpper.match(/X([-+]?\d*\.?\d+)/);
            const yMatch = linhaUpper.match(/Y([-+]?\d*\.?\d+)/);
            const zMatch = linhaUpper.match(/Z([-+]?\d*\.?\d+)/);
            
            if (xMatch) x = parseFloat(xMatch[1]);
            if (yMatch) y = parseFloat(yMatch[1]);
            if (zMatch) z = parseFloat(zMatch[1]);
            
            pontos.push({ x, y, z, tipo: tipoAtual });
        }
        
        return pontos;
    }
    
    /**
     * Ajusta a câmera para enquadrar toda a trajetória
     * @param {Array} pontos - Array de pontos
     */
    fitToView(pontos) {
        if (pontos.length === 0) return;
        
        // Calcula limites
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;
        
        pontos.forEach(p => {
            minX = Math.min(minX, p.x);
            maxX = Math.max(maxX, p.x);
            minY = Math.min(minY, p.y);
            maxY = Math.max(maxY, p.y);
            minZ = Math.min(minZ, p.z);
            maxZ = Math.max(maxZ, p.z);
        });
        
        // Calcula centro e tamanho
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const centerZ = (minZ + maxZ) / 2;
        const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
        const distance = Math.max(size * 1.5, 80);
        
        // Posiciona câmera e alvo
        this.controls.target.set(centerX, centerZ, centerY);
        this.camera.position.set(centerX + distance, centerZ + distance, centerY + distance);
        this.controls.update();
    }
    
    /**
     * Muda a vista para uma orientação específica
     * @param {string} view - 'top', 'front', 'side', 'iso'
     */
    setView(view) {
        const target = this.controls.target;
        const distance = 120;
        
        switch(view) {
            case 'top':
                this.camera.position.set(target.x, target.y + distance, target.z);
                break;
            case 'front':
                this.camera.position.set(target.x, target.y, target.z + distance);
                break;
            case 'side':
                this.camera.position.set(target.x + distance, target.y, target.z);
                break;
            case 'iso':
                this.camera.position.set(target.x + distance, target.y + distance, target.z + distance);
                break;
            default:
                return;
        }
        this.controls.update();
    }
    
    /**
     * Reset da câmera para posição padrão
     */
    resetView() {
        this.controls.target.set(0, 0, 0);
        this.camera.position.set(150, 150, 150);
        this.controls.update();
    }
    
    /**
     * Limpa todas as linhas e pontos da cena
     */
    clear() {
        this.lines.forEach(line => this.scene.remove(line));
        this.spheres.forEach(sphere => this.scene.remove(sphere));
        this.lines = [];
        this.spheres = [];
    }
    
    /**
     * Redimensiona o canvas quando a janela muda
     */
    onResize() {
        if (!this.container) return;
        
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        
        if (width === 0 || height === 0) return;
        
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
        if (this.labelRenderer) this.labelRenderer.setSize(width, height);
    }
    
    /**
     * Loop de animação
     */
    animate() {
        requestAnimationFrame(() => this.animate());
        
        if (this.controls) this.controls.update();
        
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
        
        if (this.labelRenderer && this.scene && this.camera) {
            this.labelRenderer.render(this.scene, this.camera);
        }
    }
}
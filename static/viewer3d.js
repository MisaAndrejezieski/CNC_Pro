// static/viewer3d.js - Visualizador 3D de G-code

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';

export class GCodeViewer3D {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('Container não encontrado:', containerId);
            return;
        }
        
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.labelRenderer = null;
        this.controls = null;
        this.lines = [];
        this.spheres = [];
        
        this.init();
    }
    
    init() {
        // Cena
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);
        this.scene.fog = new THREE.FogExp2(0x1a1a2e, 0.0005);
        
        // Câmera
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
        this.camera.position.set(150, 150, 150);
        this.camera.lookAt(0, 0, 0);
        
        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);
        
        // Label Renderer
        this.labelRenderer = new CSS2DRenderer();
        this.labelRenderer.setSize(width, height);
        this.labelRenderer.domElement.style.position = 'absolute';
        this.labelRenderer.domElement.style.top = '0px';
        this.labelRenderer.domElement.style.left = '0px';
        this.labelRenderer.domElement.style.pointerEvents = 'none';
        this.container.appendChild(this.labelRenderer.domElement);
        
        // Controles
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.rotateSpeed = 1.0;
        this.controls.zoomSpeed = 1.2;
        this.controls.panSpeed = 0.8;
        
        // Iluminação
        this.addLights();
        
        // Grid e eixos
        this.addGrid();
        this.addAxes();
        
        // Anima
        this.animate();
        
        // Resize
        window.addEventListener('resize', () => this.onResize());
    }
    
    addLights() {
        const ambientLight = new THREE.AmbientLight(0x404060);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(50, 100, 50);
        directionalLight.castShadow = true;
        this.scene.add(directionalLight);
        
        const fillLight = new THREE.PointLight(0x4466cc, 0.3);
        fillLight.position.set(-30, 20, 30);
        this.scene.add(fillLight);
        
        const backLight = new THREE.PointLight(0xffaa44, 0.2);
        backLight.position.set(0, 30, -50);
        this.scene.add(backLight);
    }
    
    addGrid() {
        const gridHelper = new THREE.GridHelper(200, 20, 0x4488aa, 0x335566);
        gridHelper.position.y = -0.1;
        this.scene.add(gridHelper);
        
        const fineGrid = new THREE.GridHelper(200, 100, 0x336677, 0x224455);
        fineGrid.position.y = -0.05;
        this.scene.add(fineGrid);
    }
    
    addAxes() {
        const xAxis = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), 50, 0xff3333);
        const yAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 50, 0x33ff33);
        const zAxis = new THREE.ArrowHelper(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), 50, 0x3399ff);
        this.scene.add(xAxis, yAxis, zAxis);
        
        const makeLabel = (text, color, position) => {
            const div = document.createElement('div');
            div.textContent = text;
            div.style.color = color;
            div.style.fontSize = '16px';
            div.style.fontWeight = 'bold';
            div.style.textShadow = '1px 1px 0px black';
            const label = new CSS2DObject(div);
            label.position.copy(position);
            this.scene.add(label);
        };
        
        makeLabel('X', '#ff6666', new THREE.Vector3(55, -5, -5));
        makeLabel('Y', '#66ff66', new THREE.Vector3(-5, 55, -5));
        makeLabel('Z', '#66aaff', new THREE.Vector3(-5, -5, 55));
    }
    
    loadGCode(gcode) {
        // Limpa linhas anteriores
        this.lines.forEach(line => this.scene.remove(line));
        this.spheres.forEach(sphere => this.scene.remove(sphere));
        this.lines = [];
        this.spheres = [];
        
        const pontos = this.parseGCode(gcode);
        if (pontos.length === 0) return;
        
        const materialCorte = new THREE.LineBasicMaterial({ color: 0x00ff88, linewidth: 2 });
        const materialRapido = new THREE.LineBasicMaterial({ color: 0x888888, linewidth: 1 });
        
        let segmentoAtual = [];
        let tipoAtual = null;
        
        for (let i = 0; i < pontos.length; i++) {
            const p = pontos[i];
            
            if (tipoAtual !== p.tipo && segmentoAtual.length > 1) {
                this.drawSegment(segmentoAtual, tipoAtual === 'corte' ? materialCorte : materialRapido);
                segmentoAtual = [];
            }
            
            segmentoAtual.push(new THREE.Vector3(p.x, p.z, p.y));
            tipoAtual = p.tipo;
        }
        
        if (segmentoAtual.length > 1) {
            this.drawSegment(segmentoAtual, tipoAtual === 'corte' ? materialCorte : materialRapido);
        }
        
        this.addSpecialPoints(pontos);
        this.fitToView(pontos);
    }
    
    drawSegment(pontos, material) {
        const geometry = new THREE.BufferGeometry();
        const vertices = [];
        pontos.forEach(p => vertices.push(p.x, p.y, p.z));
        geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(vertices), 3));
        const line = new THREE.Line(geometry, material);
        this.scene.add(line);
        this.lines.push(line);
    }
    
    addSpecialPoints(pontos) {
        if (pontos.length === 0) return;
        
        const startPoint = pontos[0];
        const startSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.5, 16, 16),
            new THREE.MeshStandardMaterial({ color: 0x33ff33, emissive: 0x116611 })
        );
        startSphere.position.set(startPoint.x, startPoint.z, startPoint.y);
        this.scene.add(startSphere);
        this.spheres.push(startSphere);
        
        const endPoint = pontos[pontos.length - 1];
        const endSphere = new THREE.Mesh(
            new THREE.SphereGeometry(1.5, 16, 16),
            new THREE.MeshStandardMaterial({ color: 0xff3333, emissive: 0x661111 })
        );
        endSphere.position.set(endPoint.x, endPoint.z, endPoint.y);
        this.scene.add(endSphere);
        this.spheres.push(endSphere);
        
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
                new THREE.SphereGeometry(1.2, 16, 16),
                new THREE.MeshStandardMaterial({ color: 0xff6600, emissive: 0x442200 })
            );
            depthSphere.position.set(deepestPoint.x, deepestPoint.z, deepestPoint.y);
            this.scene.add(depthSphere);
            this.spheres.push(depthSphere);
        }
    }
    
    parseGCode(gcode) {
        const linhas = gcode.split('\n');
        const pontos = [];
        let x = 0, y = 0, z = 0;
        let tipoAtual = 'rapido';
        
        for (const linha of linhas) {
            const linhaUpper = linha.toUpperCase();
            
            if (linhaUpper.startsWith('G0')) {
                tipoAtual = 'rapido';
            } else if (linhaUpper.startsWith('G1')) {
                tipoAtual = 'corte';
            } else {
                continue;
            }
            
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
    
    fitToView(pontos) {
        if (pontos.length === 0) return;
        
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
        
        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const centerZ = (minZ + maxZ) / 2;
        const size = Math.max(maxX - minX, maxY - minY, maxZ - minZ);
        const distance = Math.max(size * 1.5, 100);
        
        this.controls.target.set(centerX, centerZ, centerY);
        this.camera.position.set(centerX + distance, centerZ + distance, centerY + distance);
        this.controls.update();
    }
    
    setView(view) {
        const target = this.controls.target;
        const distance = 150;
        
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
        }
        this.controls.update();
    }
    
    resetView() {
        this.controls.target.set(0, 0, 0);
        this.camera.position.set(150, 150, 150);
        this.controls.update();
    }
    
    onResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
        if (this.labelRenderer) this.labelRenderer.setSize(width, height);
    }
    
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
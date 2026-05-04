// api/gerar.js
export default async function handler(req, res) {
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
        const { largura = 100, altura = 100, profundidade = 3 } = req.body;
        
        const gcode = `(CNC Pro)
(Largura: ${largura} mm, Altura: ${altura} mm)
(Profundidade: ${profundidade} mm)
G90 G21
M3 S10000
G0 Z5.0
G0 X0 Y0
G1 Z-${profundidade} F800
G1 X${largura} Y0
G1 X${largura} Y${altura}
G1 X0 Y${altura}
G1 X0 Y0
G0 Z5.0
M5
G0 X0 Y0
M30`;

        return res.status(200).json({
            success: true,
            gcode: gcode,
            linhas: gcode.split('\n').length
        });
        
    } catch (error) {
        return res.status(500).json({ success: false, error: error.message });
    }
}
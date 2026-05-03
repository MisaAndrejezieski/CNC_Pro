"""Gerenciador de configurações"""

import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerencia configurações do aplicativo"""
    
    DEFAULT_CONFIG = {
        'dimensoes': {
            'largura': 100.0,
            'altura': 100.0
        },
        'resolucao': 10.0,
        'profundidade': 3.0,
        'passo_corte': 0.5,
        'velocidade_corte': 800.0,
        'velocidade_rapida': 3500.0,
        'limiar': 128,
        'diametro_ferramenta': 0.4,
        'sobreposicao': 0.4,
        'altura_seguranca': 5.0,
        'estrategia': 'zig_zag',
        'suavizar': False,
        'ultimos_arquivos': []
    }
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self.load()
    
    def load(self) -> Dict[str, Any]:
        """Carrega configuração do arquivo"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # Merge com defaults
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    
                    # Remove chaves extras se necessário
                    for key in list(config.keys()):
                        if key not in self.DEFAULT_CONFIG:
                            del config[key]
                    
                    return config
            else:
                # Cria arquivo padrão
                self.save(self.DEFAULT_CONFIG)
                return self.DEFAULT_CONFIG.copy()
                
        except Exception as e:
            logger.error(f"Erro ao carregar config: {e}")
            return self.DEFAULT_CONFIG.copy()
    
    def save(self, config: Dict[str, Any]) -> bool:
        """Salva configuração no arquivo"""
        try:
            # Atualiza configuração atual
            self.config.update(config)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            logger.info("Configuração salva")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar config: {e}")
            return False
    
    def get(self, key: str, default=None):
        """Obtém um valor da configuração"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """Define um valor na configuração"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        return self.save(self.config)
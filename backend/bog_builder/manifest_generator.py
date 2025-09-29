"""
Manifest-based wire sheet generator for PyBOG.
Allows declarative specification of wire sheets via YAML/JSON.
"""

import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Add the bog_builder to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bog_builder import BogFolderBuilder

class LayoutStyle(Enum):
    """Available layout styles"""
    HIERARCHICAL = "hierarchical"
    COMPACT = "compact"
    SPACIOUS = "spacious"
    FORCE_DIRECTED = "force_directed"

class WireRouting(Enum):
    """Wire routing styles"""
    DIRECT = "direct"
    ORTHOGONAL = "orthogonal"
    CURVED = "curved"

@dataclass
class ComponentSpec:
    """Component specification from manifest"""
    type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[List[int]] = None
    annotation: Optional[str] = None

@dataclass
class ConnectionSpec:
    """Connection specification from manifest"""
    source: str  # Format: "ComponentName.slotName"
    target: str  # Format: "ComponentName.slotName"
    annotation: Optional[str] = None

@dataclass
class FolderSpec:
    """Folder specification from manifest"""
    name: str
    components: List[ComponentSpec] = field(default_factory=list)
    subfolders: List['FolderSpec'] = field(default_factory=list)

@dataclass
class ManifestSpec:
    """Complete manifest specification"""
    metadata: Dict[str, Any]
    layout: Dict[str, Any]
    folders: List[FolderSpec]
    connections: List[ConnectionSpec]
    templates: List[str] = field(default_factory=list)

class ManifestGenerator:
    """Generate BOG files from manifest specifications"""
    
    # Extended component registry with missing components
    EXTENDED_COMPONENTS = {
        # Additional math components
        "kitControl:Power": {"inputs": ["base", "exponent"], "outputs": ["out"]},
        "kitControl:SquareRoot": {"inputs": ["in"], "outputs": ["out"]},
        "kitControl:Absolute": {"inputs": ["in"], "outputs": ["out"]},
        "kitControl:Round": {"inputs": ["in"], "outputs": ["out"]},
        "kitControl:Modulo": {"inputs": ["dividend", "divisor"], "outputs": ["out"]},
        
        # Signal processing
        "kitControl:RateLimit": {"inputs": ["in", "rateLimit"], "outputs": ["out"]},
        "kitControl:Hysteresis": {"inputs": ["in", "highLimit", "lowLimit"], "outputs": ["out"]},
        "kitControl:Deadband": {"inputs": ["in", "deadband"], "outputs": ["out"]},
        "kitControl:Filter": {"inputs": ["in", "timeConstant"], "outputs": ["out"]},
        
        # Statistical
        "kitControl:StandardDeviation": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
        "kitControl:Median": {"inputs": ["inA", "inB", "inC", "inD"], "outputs": ["out"]},
        
        # Timers
        "kitControl:TimerOn": {"inputs": ["in", "delay"], "outputs": ["out"]},
        "kitControl:TimerOff": {"inputs": ["in", "delay"], "outputs": ["out"]},
        "kitControl:Interval": {"inputs": ["enable", "interval"], "outputs": ["out"]},
        "kitControl:Stopwatch": {"inputs": ["start", "stop", "reset"], "outputs": ["elapsed"]},
    }
    
    def __init__(self, manifest_path: str):
        """Initialize with manifest file path"""
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_manifest()
        self.builder = None
        self.component_map = {}  # Map component names to their folder paths
        
    def _load_manifest(self) -> ManifestSpec:
        """Load and parse manifest file"""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")
        
        # Load raw data
        if self.manifest_path.suffix == '.yaml' or self.manifest_path.suffix == '.yml':
            with open(self.manifest_path, 'r') as f:
                data = yaml.safe_load(f)
        elif self.manifest_path.suffix == '.json':
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
        else:
            raise ValueError(f"Unsupported manifest format: {self.manifest_path.suffix}")
        
        # Parse into structured format
        return self._parse_manifest(data)
    
    def _parse_manifest(self, data: Dict) -> ManifestSpec:
        """Parse raw manifest data into structured format"""
        # Parse folders recursively
        folders = []
        for folder_data in data.get('folders', []):
            folders.append(self._parse_folder(folder_data))
        
        # Parse connections
        connections = []
        for conn_data in data.get('connections', []):
            connections.append(ConnectionSpec(
                source=conn_data['source'],
                target=conn_data['target'],
                annotation=conn_data.get('annotation')
            ))
        
        return ManifestSpec(
            metadata=data.get('metadata', {}),
            layout=data.get('layout', {}),
            folders=folders,
            connections=connections,
            templates=data.get('templates', [])
        )
    
    def _parse_folder(self, folder_data: Dict) -> FolderSpec:
        """Parse folder specification"""
        components = []
        for comp_data in folder_data.get('components', []):
            components.append(ComponentSpec(
                type=comp_data['type'],
                name=comp_data['name'],
                properties=comp_data.get('properties', {}),
                position=comp_data.get('position'),
                annotation=comp_data.get('annotation')
            ))
        
        subfolders = []
        for subfolder_data in folder_data.get('subfolders', []):
            subfolders.append(self._parse_folder(subfolder_data))
        
        return FolderSpec(
            name=folder_data['name'],
            components=components,
            subfolders=subfolders
        )
    
    def generate(self, output_path: Optional[str] = None) -> str:
        """Generate BOG file from manifest"""
        # Initialize builder
        root_name = self.manifest.metadata.get('name', 'WireSheet')
        self.builder = BogFolderBuilder(root_name, debug=True)
        
        # Apply templates
        for template_name in self.manifest.templates:
            self._apply_template(template_name)
        
        # Process folders
        for folder in self.manifest.folders:
            self._process_folder(folder, is_root=(folder.name == root_name))
        
        # Process connections
        for connection in self.manifest.connections:
            self._process_connection(connection)
        
        # Determine output path
        if output_path is None:
            output_path = f"{root_name}.bog"
        
        # Save BOG file
        self.builder.save(output_path)
        print(f"Generated BOG file: {output_path}")
        
        return output_path
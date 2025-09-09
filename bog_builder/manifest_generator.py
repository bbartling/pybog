"""
Manifest-based wire sheet generator for PyBOG.
Allows declarative specification of wire sheets via YAML/JSON.
"""

import yaml
import json
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
    
    def _process_folder(self, folder: FolderSpec, is_root: bool = False):
        """Process folder and its contents"""
        # Start subfolder if not root
        if not is_root:
            self.builder.start_sub_folder(folder.name)
        
        # Process components in folder
        for component in folder.components:
            self._create_component(component)
            # Track component location for connection resolution
            folder_path = self.builder.get_current_path_str()
            self.component_map[component.name] = folder_path
        
        # Process subfolders
        for subfolder in folder.subfolders:
            self._process_folder(subfolder, is_root=False)
        
        # End subfolder if not root
        if not is_root:
            self.builder.end_sub_folder()
    
    def _create_component(self, component: ComponentSpec):
        """Create a component based on its specification"""
        comp_type = component.type
        
        # Handle writable components
        if comp_type == "NumericWritable":
            value = component.properties.get('value', 0.0)
            self.builder.add_numeric_writable(component.name, value)
        elif comp_type == "BooleanWritable":
            value = component.properties.get('value', False)
            self.builder.add_boolean_writable(component.name, value)
        elif comp_type == "EnumWritable":
            # Handle enum writable with facets
            facets = component.properties.get('facets', '')
            default = component.properties.get('default', '0')
            self.builder.add_enum_writable(component.name, facets, default)
        
        # Handle constant components
        elif comp_type == "NumericConst":
            value = component.properties.get('value', 0.0)
            self.builder.add_numeric_const(component.name, value)
        elif comp_type == "BooleanConst":
            value = component.properties.get('value', False)
            self.builder.add_boolean_const(component.name, value)
        
        # Handle schedule components
        elif comp_type in ["BooleanSchedule", "NumericSchedule", "EnumSchedule"]:
            prefix = "sch"
            self.builder.add_component(f"{prefix}:{comp_type}", component.name, component.properties)
        
        # Handle all other control components
        else:
            # Determine the palette prefix
            if comp_type.startswith("kitControl:"):
                full_type = comp_type
            else:
                full_type = f"kitControl:{comp_type}"
            
            # Add component with properties
            self.builder.add_component(full_type, component.name, component.properties)
    
    def _process_connection(self, connection: ConnectionSpec):
        """Process a connection between components"""
        # Parse source and target
        source_parts = connection.source.split('.')
        target_parts = connection.target.split('.')
        
        if len(source_parts) != 2 or len(target_parts) != 2:
            raise ValueError(f"Invalid connection format. Expected 'Component.slot', got source='{connection.source}', target='{connection.target}'")
        
        source_name, source_slot = source_parts
        target_name, target_slot = target_parts
        
        # Create the link
        try:
            self.builder.add_link(source_name, source_slot, target_name, target_slot)
        except ValueError as e:
            print(f"Warning: Failed to create connection {connection.source} -> {connection.target}: {e}")
    
    def _apply_template(self, template_name: str):
        """Apply a predefined template"""
        templates = {
            "pid_cascade": self._template_pid_cascade,
            "vav_control": self._template_vav_control,
            "ahu_control": self._template_ahu_control,
            "chiller_sequencing": self._template_chiller_sequencing,
            "lighting_control": self._template_lighting_control
        }
        
        if template_name in templates:
            templates[template_name]()
        else:
            print(f"Warning: Unknown template '{template_name}'")
    
    def _template_pid_cascade(self):
        """Create cascaded PID control template"""
        self.builder.start_sub_folder("PID_Cascade")
        
        # Primary PID loop
        self.builder.add_component("kitControl:LoopPoint", "Primary_PID", {
            "proportionalConstant": 2.0,
            "integralConstant": 0.5
        })
        
        # Secondary PID loop  
        self.builder.add_component("kitControl:LoopPoint", "Secondary_PID", {
            "proportionalConstant": 1.0,
            "integralConstant": 0.2
        })
        
        # Cascade connection
        self.builder.add_link("Primary_PID", "out", "Secondary_PID", "setpoint")
        
        self.builder.end_sub_folder()
    
    def _template_vav_control(self):
        """Create VAV box control template"""
        self.builder.start_sub_folder("VAV_Control")
        
        # Temperature control
        self.builder.add_numeric_writable("Zone_Temp", 72.0)
        self.builder.add_numeric_writable("Zone_Setpoint", 70.0)
        
        self.builder.add_component("kitControl:LoopPoint", "Temp_PID", {
            "proportionalConstant": 2.0,
            "integralConstant": 0.5
        })
        
        # Damper control
        self.builder.add_component("kitControl:Minimum", "Min_Position")
        self.builder.add_component("kitControl:Maximum", "Max_Position")
        
        self.builder.add_numeric_writable("Damper_Position", 0.0)
        
        # Connect temperature control
        self.builder.add_link("Zone_Temp", "out", "Temp_PID", "controlledVariable")
        self.builder.add_link("Zone_Setpoint", "out", "Temp_PID", "setpoint")
        self.builder.add_link("Temp_PID", "out", "Damper_Position", "in16")
        
        self.builder.end_sub_folder()
    
    def _template_ahu_control(self):
        """Create AHU control template"""
        self.builder.start_sub_folder("AHU_Control")
        
        # Supply air temperature control
        self.builder.add_numeric_writable("Supply_Air_Temp", 55.0)
        self.builder.add_numeric_writable("Supply_Air_Setpoint", 55.0)
        
        # Mixed air temperature control
        self.builder.add_numeric_writable("Mixed_Air_Temp", 65.0)
        self.builder.add_numeric_writable("Return_Air_Temp", 72.0)
        self.builder.add_numeric_writable("Outside_Air_Temp", 85.0)
        
        # Damper control
        self.builder.add_component("kitControl:LoopPoint", "MAT_PID")
        self.builder.add_numeric_writable("OA_Damper_Position", 0.0)
        
        # Fan control
        self.builder.add_boolean_writable("Supply_Fan_Enable", True)
        self.builder.add_numeric_writable("Supply_Fan_Speed", 50.0)
        
        self.builder.end_sub_folder()
    
    def _template_chiller_sequencing(self):
        """Create chiller sequencing template"""
        self.builder.start_sub_folder("Chiller_Sequencing")
        
        # Load calculation
        self.builder.add_numeric_writable("Building_Load", 0.0)
        
        # Chiller stages
        for i in range(1, 4):
            self.builder.add_boolean_writable(f"Chiller_{i}_Enable", False)
            self.builder.add_numeric_writable(f"Chiller_{i}_Load", 0.0)
        
        # Sequencing logic
        self.builder.add_component("kitControl:GreaterThan", "Stage_2_Enable")
        self.builder.add_component("kitControl:GreaterThan", "Stage_3_Enable")
        
        self.builder.end_sub_folder()
    
    def _template_lighting_control(self):
        """Create lighting control template"""
        self.builder.start_sub_folder("Lighting_Control")
        
        # Occupancy and daylight sensors
        self.builder.add_boolean_writable("Occupancy_Sensor", False)
        self.builder.add_numeric_writable("Daylight_Level", 0.0)
        
        # Lighting zones
        for zone in ["North", "South", "East", "West"]:
            self.builder.add_numeric_writable(f"{zone}_Zone_Level", 0.0)
            self.builder.add_boolean_writable(f"{zone}_Zone_Enable", False)
        
        # Control logic
        self.builder.add_component("kitControl:And", "Lights_Enable")
        self.builder.add_component("kitControl:LessThan", "Daylight_Check")
        
        self.builder.end_sub_folder()

def main():
    """Command-line interface for manifest generator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate BOG files from manifest')
    parser.add_argument('manifest', help='Path to manifest file (YAML or JSON)')
    parser.add_argument('-o', '--output', help='Output BOG file path')
    parser.add_argument('--validate-only', action='store_true', help='Validate manifest without generating')
    
    args = parser.parse_args()
    
    try:
        generator = ManifestGenerator(args.manifest)
        
        if args.validate_only:
            print(f"Manifest '{args.manifest}' is valid")
            print(f"  Components: {sum(len(f.components) for f in generator.manifest.folders)}")
            print(f"  Connections: {len(generator.manifest.connections)}")
            print(f"  Folders: {len(generator.manifest.folders)}")
        else:
            output_path = generator.generate(args.output)
            print(f"Successfully generated: {output_path}")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

import React, { useState } from 'react';
import { 
  ChevronDown, ChevronRight, Folder, File, 
  Thermometer, Gauge, Fan, Zap, Settings2,
  FileText, FolderOpen, ArrowRight, ArrowLeft
} from 'lucide-react';

import { AnalysisData } from '../types/analysis';

interface ProjectNavigatorProps {
  analysis: AnalysisData | null;
  activeItem?: string;
  onNavigate: (elementId: string) => void;
}

const ProjectNavigator: React.FC<ProjectNavigatorProps> = ({
  analysis,
  activeItem,
  onNavigate
}) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    inputs: true,
    outputs: true,
    blocks: true,
    files: false
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getInputIcon = (input: string) => {
    const lower = input.toLowerCase();
    if (lower.includes('temperature') || lower.includes('temp')) return <Thermometer size={16} />;
    if (lower.includes('pressure')) return <Gauge size={16} />;
    if (lower.includes('fan') || lower.includes('flow')) return <Fan size={16} />;
    return <ArrowRight size={16} />;
  };

  const getOutputIcon = (output: string) => {
    const lower = output.toLowerCase();
    if (lower.includes('valve')) return <Settings2 size={16} />;
    if (lower.includes('fan')) return <Fan size={16} />;
    if (lower.includes('relay') || lower.includes('enable')) return <Zap size={16} />;
    return <ArrowLeft size={16} />;
  };

  const getBlockIcon = () => <Settings2 size={16} />;

  if (!analysis) {
    return (
      <div className="project-navigator empty">
        <div className="navigator-header">
          <Folder className="header-icon" />
          <span>Project Navigator</span>
        </div>
        <div className="empty-state">
          <FileText className="empty-icon" />
          <p>Upload HVAC documents to begin analysis</p>
        </div>
      </div>
    );
  }

  return (
    <div className="project-navigator">
      <div className="navigator-header">
        <FolderOpen className="header-icon" />
        <span>HVAC Control Project</span>
      </div>

      <div className="navigator-content">
        {/* Inputs Section */}
        <div className="nav-section">
          <div 
            className="nav-section-header"
            onClick={() => toggleSection('inputs')}
          >
            <div className="section-toggle">
              {expandedSections.inputs ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            <ArrowRight className="section-icon input-icon" />
            <span className="section-title">Inputs (AI/BI)</span>
            <span className="item-count">{analysis.inputs.length}</span>
          </div>
          
          {expandedSections.inputs && (
            <div className="nav-items">
              {analysis.inputs.map((input, index) => {
                const inputName = typeof input === 'string' ? input : input.name;
                return (
                  <div
                    key={index}
                    className={`nav-item input-item ${activeItem === inputName ? 'active' : ''}`}
                    onClick={() => onNavigate(`input-${index}`)}
                  >
                    <div className="item-icon">{getInputIcon(inputName)}</div>
                    <span className="item-label" title={inputName}>{inputName}</span>
                    <div className="pin-indicator input-pin"></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Outputs Section */}
        <div className="nav-section">
          <div 
            className="nav-section-header"
            onClick={() => toggleSection('outputs')}
          >
            <div className="section-toggle">
              {expandedSections.outputs ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            <ArrowLeft className="section-icon output-icon" />
            <span className="section-title">Outputs (AO/BO)</span>
            <span className="item-count">{analysis.outputs.length}</span>
          </div>
          
          {expandedSections.outputs && (
            <div className="nav-items">
              {analysis.outputs.map((output, index) => {
                const outputName = typeof output === 'string' ? output : output.name;
                return (
                  <div
                    key={index}
                    className={`nav-item output-item ${activeItem === outputName ? 'active' : ''}`}
                    onClick={() => onNavigate(`output-${index}`)}
                  >
                    <div className="pin-indicator output-pin"></div>
                    <div className="item-icon">{getOutputIcon(outputName)}</div>
                    <span className="item-label" title={outputName}>{outputName}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Functional Blocks Section */}
        <div className="nav-section">
          <div 
            className="nav-section-header"
            onClick={() => toggleSection('blocks')}
          >
            <div className="section-toggle">
              {expandedSections.blocks ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </div>
            <Settings2 className="section-icon" />
            <span className="section-title">Functional Blocks</span>
            <span className="item-count">{analysis.blocks.length}</span>
          </div>
          
          {expandedSections.blocks && (
            <div className="nav-items">
              {analysis.blocks.map((block, index) => {
                const blockName = typeof block === 'string' ? block : block.name;
                return (
                  <div
                    key={index}
                    className={`nav-item block-item ${activeItem === blockName ? 'active' : ''}`}
                    onClick={() => onNavigate(`block-${index}`)}
                  >
                    <div className="item-icon">{getBlockIcon()}</div>
                    <span className="item-label" title={blockName}>{blockName}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProjectNavigator;

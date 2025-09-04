import React from 'react';
import ProjectNavigator from '../../components/ProjectNavigator';
import type { AnalysisData } from '../../types/analysis';

interface ProjectTreeProps {
  analysis: AnalysisData | null;
  onNavigate: (elementId: string) => void;
}

// Thin wrapper to meet the new file structure while using existing navigator
const ProjectTree: React.FC<ProjectTreeProps> = ({ analysis, onNavigate }) => {
  return (
    <div style={{ height: '100%', background: 'transparent' }}>
      <ProjectNavigator analysis={analysis as any} onNavigate={onNavigate} />
    </div>
  );
};

export default ProjectTree;


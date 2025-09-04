// Unified Analysis Data Types

// Main analysis data structure for the application
export interface AnalysisData {
  sessionId?: string;
  inputs: Array<string | {name: string; type?: string; pin?: number}>;
  outputs: Array<string | {name: string; type?: string; pin?: number}>;
  blocks: Array<string | {name: string; type?: string; logic?: string}>;
  pseudocode: Array<string | {block?: string; logic: string[]}>;
  component_name?: string;
  component_count?: number;
  io_summary?: {
    total_inputs?: number;
    total_outputs?: number;
    has_errors?: boolean;
  };
  control_logic?: {
    complexity?: string;
    loop_count?: number;
  };
  ready_for_review?: boolean;
}

// Node-specific analysis data for ReactFlow
export interface NodeAnalysisData {
  sessionId: string;
  analysis: AnalysisData;
  onApprove?: (feedback?: string) => void;
  onRequestChanges?: (feedback: string) => void;
  approving?: boolean;
  className?: string;
}

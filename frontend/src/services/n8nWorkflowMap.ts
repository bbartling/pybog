// @ts-nocheck
import { Node, Edge } from 'react-flow-renderer';

// Minimal shape based on n8n_get_workflow_details
interface N8NWorkflow {
  workflow?: { nodes: any[]; connections: Record<string, { main: { node: string; type: string; index: number }[][] }> };
  nodes?: any[];
  connections?: Record<string, { main: { node: string; type: string; index: number }[][] }>;
}

function roleForNodeType(type: string): 'user' | 'assistant' | 'system' {
  if (type.startsWith('@n8n/n8n-nodes-langchain')) return 'assistant'; // AI tools/agent
  if (type.includes('webhook') || type.includes('httpRequest') || type.includes('postgres')) return 'system';
  if (type.includes('code') || type.includes('if') || type.includes('merge')) return 'system';
  return 'system';
}

function colorForRole(role: 'user' | 'assistant' | 'system'): string {
  switch (role) {
    case 'user':
      return '#6b5bd1';
    case 'assistant':
      return '#34a853';
    default:
      return '#9e9e9e';
  }
}

// Map n8n workflow JSON to React Flow nodes/edges for our Chat Bubble nodes
export function mapWorkflowToFlow(workflowJson: N8NWorkflow): { nodes: Node[]; edges: Edge[] } {
  const wf = workflowJson.workflow || (workflowJson as any);
  const nodesJson = wf.nodes || [];
  const connections = wf.connections || {};

  const nodes: Node[] = nodesJson.map((n: any, idx: number) => {
    const role = roleForNodeType(n.type || '');
    const x = Array.isArray(n.position) ? n.position[0] : 100 + (idx % 3) * 300;
    const y = Array.isArray(n.position) ? n.position[1] : 80 + Math.floor(idx / 3) * 160;
    return {
      id: String(n.id || n.name || idx),
      type: 'chatBubble',
      position: { x, y },
      data: {
        title: n.name || n.type,
        role,
        color: colorForRole(role),
        content: n.notes || n.type,
        timestamp: new Date(),
      },
    } as Node;
  });

  const edges: Edge[] = [];
  Object.entries(connections).forEach(([fromName, conn]) => {
    const fromNode = nodesJson.find((n: any) => n.name === fromName);
    const fromId = String(fromNode?.id || fromName);
    const mains = conn?.main || [];
    mains.forEach((outputs) => {
      outputs.forEach((out) => {
        const targetName = out.node;
        const targetNode = nodesJson.find((n: any) => n.name === targetName);
        const toId = String(targetNode?.id || targetName);
        edges.push({
          id: `${fromId}->${toId}`,
          source: fromId,
          target: toId,
          style: { stroke: '#666', strokeWidth: 2, strokeDasharray: '6 4' },
        });
      });
    });
  });

  return { nodes, edges };
}

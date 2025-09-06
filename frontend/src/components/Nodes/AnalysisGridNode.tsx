import React, { memo, useMemo, useState } from 'react';
import type { NodeProps } from 'reactflow';
import { Handle, Position } from 'reactflow';
import { Box, Stack, Typography, Button, Chip } from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';

interface AnalysisDataShape {
  inputs?: Array<string | { name: string; type?: string; units?: string }>;
  outputs?: Array<string | { name: string; type?: string; units?: string }>;
  control_blocks?: any[];
  pseudocode?: Array<{ block: string; logic: string[] }> | string[];
  io_summary?: { total_inputs?: number; total_outputs?: number; has_errors?: boolean };
}

export interface AnalysisGridNodeData {
  sessionId: string;
  analysis?: AnalysisDataShape;
  content?: string;
  approving?: boolean;
  processing?: boolean;
  onApprove?: () => void;
  onRequestChanges?: (feedback: string) => void;
}

interface Row {
  id: string;
  slot: 'IN' | 'OUT';
  name: string;
  type: string;
  out?: string;
  facets?: string;
  status?: 'ok' | 'fault' | 'alarm' | 'error';
}

const columns: GridColDef<Row>[] = [
  { field: 'slot', headerName: 'Slot', width: 70 },
  { field: 'name', headerName: 'Name', flex: 1, minWidth: 160 },
  { field: 'type', headerName: 'Type', width: 100 },
  { field: 'out', headerName: 'Out', width: 80 },
  { field: 'facets', headerName: 'Facets', width: 120 },
  {
    field: 'status',
    headerName: 'Status',
    width: 100,
    renderCell: (params) => {
      const v = params.value as Row['status'];
      const color = v === 'ok' ? 'success' : v === 'fault' ? 'warning' : v === 'alarm' ? 'error' : 'default';
      const label = v === 'ok' ? '[ok]' : v === 'fault' ? '[fault]' : v === 'alarm' ? '[alarm]' : '[—]';
      return <Chip label={label} color={color as any} size="small" variant="outlined" sx={{ height: 20 }} />;
    },
  },
];

function inferType(name: string): string {
  const s = name.toLowerCase();
  if (s.includes('temp') || s.includes('pressure') || s.includes('humid')) return 'AI';
  if (s.includes('setpoint')) return 'AO';
  if (s.includes('status') || s.includes('enable')) return 'BI';
  if (s.includes('command') || s.includes('valve') || s.includes('damper')) return 'BO';
  return 'AI';
}

const AnalysisGridNode: React.FC<NodeProps<AnalysisGridNodeData>> = ({ data }) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');

  const rows = useMemo<Row[]>(() => {
    const list: Row[] = [];
    const inputs = data.analysis?.inputs || [];
    const outputs = data.analysis?.outputs || [];

    inputs.forEach((item, idx) => {
      const name = typeof item === 'string' ? item : item.name;
      list.push({ id: `in-${idx}`, slot: 'IN', name, type: inferType(name), status: 'ok' });
    });
    outputs.forEach((item, idx) => {
      const name = typeof item === 'string' ? item : item.name;
      list.push({ id: `out-${idx}`, slot: 'OUT', name, type: inferType(name), status: 'ok' });
    });
    return list;
  }, [data.analysis]);

  return (
    <Box sx={{
      width: 560,
      height: 320,
      background: 'linear-gradient(180deg, #1f2937 0%, #0f172a 100%)',
      borderRadius: 1.5,
      border: '1px solid #334155',
      color: '#e5e7eb',
      overflow: 'hidden',
      boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
    }}>
      <Handle type="target" position={Position.Left} style={{ background: '#22d3ee' }} />
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ px: 1.5, py: 0.75, borderBottom: '1px solid #334155', background: 'linear-gradient(90deg, #0b1220 0%, #132035 100%)' }}>
        <Typography variant="body2" sx={{ color: '#93c5fd', fontWeight: 700 }}>Analysis</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" variant="contained" color="success" disabled={!!data.approving} onClick={data.onApprove} startIcon={<CheckCircleIcon fontSize="small" />} sx={{ textTransform: 'none' }}>
            {data.approving ? 'Generating…' : 'Approve'}
          </Button>
          <Button size="small" variant="outlined" color="info" onClick={() => setShowFeedback(!showFeedback)} startIcon={<EditIcon fontSize="small" />} sx={{ textTransform: 'none', borderColor: '#3b82f6', color: '#bfdbfe' }}>
            Refine
          </Button>
        </Stack>
      </Stack>
      <Box sx={{ height: showFeedback ? 200 : 260 }}>
        <DataGrid
          density="compact"
          rows={rows}
          columns={columns}
          hideFooter
          sx={{
            '& .MuiDataGrid-columnHeaders': { background: '#0b1220', color: '#e5e7eb' },
            '& .MuiDataGrid-row:hover': { background: 'rgba(34,211,238,0.06)' },
            '& .MuiDataGrid-cell': { borderColor: '#1f2937', color: '#e5e7eb' },
            '&.MuiDataGrid-root': { border: 'none' }
          }}
        />
      </Box>
      {showFeedback && (
        <Box sx={{ p: 1, borderTop: '1px solid #334155', background: 'rgba(2,6,23,0.5)' }}>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={2}
            placeholder="Describe refinement…"
            style={{ width: '100%', background: '#0b1220', color: '#e5e7eb', border: '1px solid #334155', borderRadius: 6, padding: 8, fontSize: 12 }}
          />
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Button size="small" variant="contained" disabled={!feedback.trim()} onClick={() => data.onRequestChanges?.(feedback)} sx={{ textTransform: 'none' }}>Send</Button>
            <Button size="small" variant="text" onClick={() => { setFeedback(''); setShowFeedback(false); }} sx={{ textTransform: 'none', color: '#94a3b8' }}>Cancel</Button>
          </Stack>
        </Box>
      )}
      <Handle type="source" position={Position.Right} style={{ background: '#2dd4bf' }} />
    </Box>
  );
};

export default memo(AnalysisGridNode);

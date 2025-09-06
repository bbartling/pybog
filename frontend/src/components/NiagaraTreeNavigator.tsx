import React, { memo, useEffect, useMemo, useState } from 'react';
import { Box, Chip, Stack, Typography } from '@mui/material';
import TreeView from '@mui/lab/TreeView';
import TreeItem from '@mui/lab/TreeItem';
import FolderIcon from '@mui/icons-material/Folder';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import DescriptionIcon from '@mui/icons-material/Description';
import SettingsIcon from '@mui/icons-material/Settings';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import DeviceThermostatIcon from '@mui/icons-material/DeviceThermostat';
import StreamIcon from '@mui/icons-material/Stream';
import DownloadIcon from '@mui/icons-material/Download';
import MemoryIcon from '@mui/icons-material/Memory';
import StorageIcon from '@mui/icons-material/Storage';
import apiService from '../services/apiService';
import './NiagaraTreeNavigator.css';

type ChatRow = { id: string; role: 'user'|'assistant'|'system'; text: string; ts: string; };

interface NiagaraTreeNavigatorProps {
  sessionId: string;
  currentAnalysis?: any;
}

const NiagaraTreeNavigator: React.FC<NiagaraTreeNavigatorProps> = ({ sessionId, currentAnalysis }) => {
  const [chat, setChat] = useState<ChatRow[]>([]);
  const [files, setFiles] = useState<{ id: string; name: string; size?: number }[]>([]);
  const [analysis, setAnalysis] = useState<any | null>(currentAnalysis || null);
  const [bogFiles, setBogFiles] = useState<{ id: string; name: string; url: string }[]>([]);

  useEffect(() => { setAnalysis(currentAnalysis || null); }, [currentAnalysis]);

  useEffect(() => {
    let cancelled = false;
    let refreshTimer: any = null;

    const fetchAll = async () => {
      try {
        const full = await apiService.getFullSession(sessionId);
        if (cancelled) return;
        const msgs = (full.messages || []).map((m: any) => ({ id: m.message_id, role: (m.type as any)||'system', text: String(m.content||''), ts: m.created_at||new Date().toISOString(), metadata: m.metadata||{} }));
        setChat(msgs.map((m: any) => ({ id: m.id, role: m.role, text: m.text, ts: m.ts })));

        const uploaded: {id:string;name:string;size?:number}[] = [];
        msgs.forEach((m: any, idx: number) => {
          const md: any = (full.messages[idx]?.metadata) || {};
          if (md?.files && Array.isArray(md.files)) {
            md.files.forEach((f: any, fi: number) => uploaded.push({ id: `${m.id}-f-${fi}`, name: f.name || f.filename || 'file', size: f.size }));
          }
          if (md?.filePersisted?.name) {
            uploaded.push({ id: `${m.id}-p`, name: md.filePersisted.name, size: md.filePersisted.size });
          }
        });
        setFiles(uploaded);

        const state = await apiService.getSessionState(sessionId).catch(() => null);
        const a = state?.analysis?.analysis_data || state?.analysis_data || full.analysis?.analysis_data || null;
        if (a) setAnalysis(a);

        const bog = msgs.filter((m: any, i: number) => (full.messages[i]?.metadata?.downloadUrl)).map((m: any, i: number) => ({ id: m.id, name: (full.messages[i]?.metadata?.fileName) || `BOG_${i+1}.bog`, url: full.messages[i]?.metadata?.downloadUrl }));
        setBogFiles(bog);
      } catch { /* ignore */ }
    };

    fetchAll();

    // Subscribe to SSE and debounce refresh
    const sub = apiService.subscribeToSessionEvents(
      sessionId,
      () => {
        if (refreshTimer) clearTimeout(refreshTimer);
        refreshTimer = setTimeout(fetchAll, 250);
      },
      () => {}
    );

    return () => { cancelled = true; if (sub) sub.close(); if (refreshTimer) clearTimeout(refreshTimer); };
  }, [sessionId]);

  const onDragStart = (evt: React.DragEvent, payload: any) => {
    evt.dataTransfer.setData('application/reactflow', JSON.stringify(payload));
    evt.dataTransfer.effectAllowed = 'move';
  };

  const InputOutputSection = useMemo(() => {
    const ins: string[] = analysis?.inputs || analysis?.io_points?.inputs || [];
    const outs: string[] = analysis?.outputs || analysis?.io_points?.outputs || [];
    return (
      <>
        <TreeItem nodeId="io" label={<Label icon={<MemoryIcon fontSize="small" />} text={`I/O Points (${ins.length + outs.length})`} /> }>
          <TreeItem nodeId="io-in" label={<Label icon={<DeviceThermostatIcon fontSize="small" />} text={`Inputs (${ins.length})`} /> }>
            {ins.map((name: string, idx: number) => (
              <TreeItem key={`in-${idx}`} nodeId={`in-${idx}`} onDragStart={(e: React.DragEvent)=>onDragStart(e,{ type:'analysis-point', id:`in-${idx}`, name, slot:'IN' })} draggable label={
                <Row icon={<ThermostatIcon fontSize="small" />} primary={name} />
              } />
            ))}
          </TreeItem>
          <TreeItem nodeId="io-out" label={<Label icon={<SettingsIcon fontSize="small" />} text={`Outputs (${outs.length})`} /> }>
            {outs.map((name: string, idx: number) => (
              <TreeItem key={`out-${idx}`} nodeId={`out-${idx}`} onDragStart={(e: React.DragEvent)=>onDragStart(e,{ type:'analysis-point', id:`out-${idx}`, name, slot:'OUT' })} draggable label={
                <Row icon={<StreamIcon fontSize="small" />} primary={name} />
              } />
            ))}
          </TreeItem>
        </TreeItem>
      </>
    );
  }, [analysis]);

  return (
    <Box sx={{ width: 300, height: '100%', background: '#f8f9fa', color: '#374151', borderRight: '1px solid #e5e7eb', overflow: 'auto' }}>
      <Box sx={{ p: 1, borderBottom: '1px solid #e5e7eb', background: '#ffffff', display:'flex', alignItems:'center', gap:1 }}>
        <StorageIcon fontSize="small" sx={{ color: '#7c3aed' }} />
        <Typography variant="subtitle2" sx={{ color: '#374151', fontWeight: 600 }}>Project Navigator</Typography>
        <Typography variant="caption" sx={{ color: '#6b7280', ml: 1 }}>Session {sessionId}</Typography>
      </Box>
      <TreeView defaultExpandAll sx={{ px:1, '& .MuiTreeItem-content.Mui-focused, & .MuiTreeItem-content.Mui-selected': { background: '#ede9fe' }, '& .MuiTreeItem-label': { color: '#374151' } }}>
        {/* Chat History */}
        <TreeItem nodeId="chat" label={<Label icon={<FolderIcon fontSize="small" />} text="Chat History" /> }>
          {chat.map((m) => (
            <TreeItem key={m.id} nodeId={`chat-${m.id}`} onDragStart={(e: React.DragEvent)=>onDragStart(e,{ type:'message', id:m.id, role:m.role, text:m.text })} draggable label={
              <Row icon={<DescriptionIcon fontSize="small" />} primary={m.text} chip={m.role} />
            } />
          ))}
        </TreeItem>

        {/* Uploaded Files */}
        <TreeItem nodeId="files" label={<Label icon={<FolderOpenIcon fontSize="small" />} text={`Uploaded Files (${files.length})`} /> }>
          {files.map((f) => (
            <TreeItem key={f.id} nodeId={`file-${f.id}`} onDragStart={(e: React.DragEvent)=>onDragStart(e,{ type:'file', id:f.id, name:f.name })} draggable label={
              <Row icon={<DescriptionIcon fontSize="small" />} primary={f.name} />
            } />
          ))}
        </TreeItem>

        {/* Analysis */}
        {analysis && (
          <TreeItem nodeId="analysis" label={<Label icon={<MemoryIcon fontSize="small" />} text="Analysis" /> }>
            {InputOutputSection}
            {/* Sequences */}
            {Array.isArray(analysis?.pseudocode) && (
              <TreeItem nodeId="sequences" label={<Label icon={<SettingsIcon fontSize="small" />} text={`Sequences (${analysis.pseudocode.length})`} /> }>
                {analysis.pseudocode.map((pc: any, idx: number) => (
                  <TreeItem key={`pc-${idx}`} nodeId={`pc-${idx}`} onDragStart={(e: React.DragEvent)=>onDragStart(e,{ type:'sequence', id:`pc-${idx}`, name: pc.block || `Sequence ${idx+1}`, text: Array.isArray(pc.logic)? pc.logic.join('\n'): String(pc) })} draggable label={
                    <Row icon={<SettingsIcon fontSize="small" />} primary={pc.block || `Sequence ${idx+1}`} />
                  } />
                ))}
              </TreeItem>
            )}
          </TreeItem>
        )}

        {/* BOG Files */}
        <TreeItem nodeId="bog" label={<Label icon={<DownloadIcon fontSize="small" />} text={`Generated Files (${bogFiles.length})`} /> }>
          {bogFiles.map((b) => (
            <TreeItem key={b.id} nodeId={`bog-${b.id}`} label={
              <Row icon={<DownloadIcon fontSize="small" />} primary={b.name} suffix={<a href={b.url} target="_blank" rel="noreferrer" style={{ color:'#fb923c', textDecoration:'none' }}>Download</a>} />
            } />
          ))}
        </TreeItem>
      </TreeView>
    </Box>
  );
};

function Label({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      {icon}
      <Typography variant="body2" sx={{ color: '#374151' }}>{text}</Typography>
    </Stack>
  );
}

function Row({ icon, primary, chip, suffix }: { icon: React.ReactNode; primary: string; chip?: string; suffix?: React.ReactNode }) {
  return (
    <Stack direction="row" alignItems="center" spacing={1} sx={{ pr: 1 }}>
      {icon}
      <Typography variant="body2" noWrap sx={{ flex:1, maxWidth: 190 }}>{primary}</Typography>
      {chip && <Chip label={chip} size="small" sx={{ height: 18 }} />}
      {suffix}
    </Stack>
  );
}

export default memo(NiagaraTreeNavigator);

import React from 'react';

export type StatusKind = 'ok' | 'warn' | 'fault' | 'pending';
export type Tone = 'system' | 'user' | 'tool';

export function StatusPuck({ status }: { status: StatusKind }) {
  const color =
    status === 'ok'
      ? '#10b981'
      : status === 'warn'
      ? '#f59e0b'
      : status === 'fault'
      ? '#ef4444'
      : '#0ea5e9';
  return (
    <span
      style={{
        display: 'inline-block',
        width: 10,
        height: 10,
        borderRadius: '9999px',
        background: color,
        boxShadow: '0 0 0 2px rgba(255,255,255,0.9)'
      }}
    />
  );
}

export function NodeChrome({
  title,
  status,
  tone,
  children
}: {
  title: string;
  status?: StatusKind;
  tone: Tone;
  children: React.ReactNode;
}) {
  const headerBg = tone === 'user' ? '#e7e7fb' : tone === 'system' ? '#e6ebf5' : '#e9f7ef';
  const headerFg = tone === 'user' ? '#4338ca' : tone === 'system' ? '#334155' : '#065f46';
  const border = tone === 'user' ? '#c4b5fd' : tone === 'system' ? '#e5e7eb' : '#a7f3d0';
  const containerBg = tone === 'user' ? '#ffffff' : tone === 'system' ? '#f8fbff' : '#f8fffb';

  return (
    <div
      style={{
        background: containerBg,
        padding: '0 0 10px 0',
        borderRadius: 12,
        border: `2px solid ${border}`,
        color: '#111827',
        fontFamily:
          'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',
        position: 'relative',
        width: 340,
      }}
    >
      <div
        style={{
          background: headerBg,
          color: headerFg,
          fontWeight: 700,
          padding: '6px 10px',
          borderTopLeftRadius: 10,
          borderTopRightRadius: 10,
          borderBottom: `1px solid ${border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span>{title}</span>
        {status ? <StatusPuck status={status} /> : null}
      </div>
      <div style={{ padding: '8px 12px' }}>{children}</div>
    </div>
  );
}

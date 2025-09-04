import React from 'react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}) => {
  if (!isOpen) return null;
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000
    }}>
      <div style={{ background: 'white', borderRadius: 8, width: 360, boxShadow: '0 10px 30px rgba(0,0,0,0.2)' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', fontWeight: 700 }}>{title}</div>
        <div style={{ padding: '12px 16px', color: '#374151', fontSize: 14 }}>{message}</div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '12px 16px', borderTop: '1px solid #e5e7eb' }}>
          <button onClick={onCancel} style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 6, background: '#f8fafc', color: '#111827' }}>{cancelLabel}</button>
          <button onClick={onConfirm} style={{ padding: '8px 12px', border: 'none', borderRadius: 6, background: '#ef4444', color: 'white', fontWeight: 600 }}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;

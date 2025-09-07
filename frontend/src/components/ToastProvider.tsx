import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type ToastLevel = 'success' | 'info' | 'warning' | 'error';

export interface Toast {
  id: string;
  level: ToastLevel;
  title: string;
  message?: string;
  timeout?: number;
}

interface ToastContextValue {
  addToast: (level: ToastLevel, title: string, message?: string, timeout?: number) => void;
}

const ToastContext = createContext<ToastContextValue>({ addToast: () => {} });

export const useToast = () => useContext(ToastContext);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((level: ToastLevel, title: string, message?: string, timeout: number = 3500) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [...prev, { id, level, title, message, timeout }]);
    if (timeout > 0) {
      setTimeout(() => removeToast(id), timeout);
    }
  }, [removeToast]);

  const value = useMemo(() => ({ addToast }), [addToast]);

  const bgFor = (lvl: ToastLevel) => ({
    success: '#D6F3D7',
    info: '#E6F3FE',
    warning: '#FFF0CC',
    error: '#FDE2E2',
  }[lvl]);

  const borderFor = (lvl: ToastLevel) => ({
    success: '#2DB72D',
    info: '#4A9EFF',
    warning: '#FFA500',
    error: '#FF4444',
  }[lvl]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div style={{ position: 'fixed', top: 12, right: 12, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {toasts.map((t) => (
          <div key={t.id} style={{
            minWidth: 280,
            maxWidth: 480,
            padding: '10px 14px',
            border: `2px solid ${borderFor(t.level)}`,
            borderRadius: 12,
            background: bgFor(t.level),
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)'
          }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: '#1F1F1F' }}>{t.title}</div>
            {t.message && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#3F3F4B' }}>{t.message}</div>
            )}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};


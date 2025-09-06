import React from 'react';
import { MessageSquare, Settings, Search, CheckCircle, Package } from 'lucide-react';

interface SwimlaneBounds {
  y: number;
  height: number;
  label: string;
  icon: React.ReactNode;
  color: string;
}

export const ConversationSwimlanes: React.FC = () => {
  const CANVAS_WIDTH = 1400;
  const lanes: SwimlaneBounds[] = [
    { 
      y: 0, 
      height: 300, 
      label: 'USER INPUT', 
      icon: <MessageSquare size={16} />,
      color: '#8b5cf6'
    },
    { 
      y: 300, 
      height: 200, 
      label: 'PROCESSING', 
      icon: <Settings size={16} />,
      color: '#64748b'
    },
    { 
      y: 500, 
      height: 300, 
      label: 'ANALYSIS', 
      icon: <Search size={16} />,
      color: '#3b82f6'
    },
    { 
      y: 800, 
      height: 250, 
      label: 'REVIEW', 
      icon: <CheckCircle size={16} />,
      color: '#10b981'
    },
    { 
      y: 1050, 
      height: 200, 
      label: 'OUTPUT', 
      icon: <Package size={16} />,
      color: '#f59e0b'
    },
  ];

  return (
    <div 
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        pointerEvents: 'none',
        zIndex: 0,
      }}
    >
      {lanes.map((lane, index) => (
        <div
          key={index}
          style={{
            position: 'absolute',
            top: lane.y,
            left: 0,
            width: CANVAS_WIDTH,
            height: lane.height,
            borderBottom: `1px solid rgba(148, 163, 184, 0.15)`,
            background: `linear-gradient(180deg, 
              rgba(${hexToRgb(lane.color)}, 0.02) 0%, 
              rgba(${hexToRgb(lane.color)}, 0) 100%)`,
          }}
        >
          {/* Lane Header */}
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: lane.color,
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.05em',
              opacity: 0.7,
            }}
          >
            {lane.icon}
            <span>{lane.label}</span>
          </div>

          {/* Visual guide lines */}
          {index === 0 && (
            <>
              <div
                style={{
                  position: 'absolute',
                  left: 200 + 170, // User message center
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: `linear-gradient(180deg, ${lane.color}40 0%, transparent 100%)`,
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  right: 200 + 170, // Assistant message center
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: `linear-gradient(180deg, ${lane.color}40 0%, transparent 100%)`,
                }}
              />
            </>
          )}

          {/* Center line for process nodes */}
          {index === 1 && (
            <div
              style={{
                position: 'absolute',
                left: CANVAS_WIDTH / 2,
                top: 0,
                bottom: 0,
                width: 1,
                background: `${lane.color}20`,
                borderLeft: `1px dashed ${lane.color}30`,
              }}
            />
          )}
        </div>
      ))}

      {/* Conversation flow indicators */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: CANVAS_WIDTH,
          height: 1250,
          pointerEvents: 'none',
        }}
      >
        {/* Left conversation path */}
        <path
          d={`M 370 100 L 370 1150`}
          stroke="#8b5cf6"
          strokeWidth="1"
          strokeDasharray="2 4"
          opacity="0.15"
          fill="none"
        />
        
        {/* Right conversation path */}
        <path
          d={`M ${CANVAS_WIDTH - 370} 100 L ${CANVAS_WIDTH - 370} 1150`}
          stroke="#3b82f6"
          strokeWidth="1"
          strokeDasharray="2 4"
          opacity="0.15"
          fill="none"
        />

        {/* Zigzag pattern hint */}
        <path
          d={`M 370 150 C ${CANVAS_WIDTH/2} 200, ${CANVAS_WIDTH/2} 250, ${CANVAS_WIDTH - 370} 300`}
          stroke="#94a3b8"
          strokeWidth="1"
          strokeDasharray="3 5"
          opacity="0.1"
          fill="none"
        />
      </svg>
    </div>
  );
};

// Helper function to convert hex to RGB
function hexToRgb(hex: string): string {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}`
    : '0, 0, 0';
}

export default ConversationSwimlanes;

// Neubrutalism Design System for PyBOG N4 Builder
// Based on the modern neubrutalism aesthetic with bold borders and flat design

export const TOKENS = {
  // Core Colors
  bg: "#F7F8FA",           // Main background
  grid: "#E9EBF2",         // Grid lines
  border: "#3F3F4B",       // Primary border color
  text: "#1F1F1F",         // Primary text
  muted: "#6D6E7A",        // Muted/secondary text
  
  // Component Colors
  nodeHeader: "#C9C7DF",   // Header backgrounds (light purple)
  nodeFooter: "#F6F2C7",   // Footer backgrounds (light yellow)
  chip: "#ECEEF5",         // Badge/chip backgrounds
  port: "#59586A",         // Connection points
  
  // Status Colors
  ok: "#2DB72D",           // Success/healthy
  warning: "#FFA500",      // Warning states
  error: "#FF4444",        // Error states
  info: "#4A9EFF",         // Info/primary actions
  
  // Role-based Colors
  userHeader: "#C9C7DF",
  userBody: "#DBDAF5",
  systemHeader: "#D0D6D7",
  systemBody: "#D4F5E5",
  processHeader: "#BFE4FB",
  processBody: "#E6F3FE",
  
  // Special States
  awaitingApproval: "#F6F2C7",
  changesRequested: "#FFF0CC",
  approved: "#D6F3D7",
  running: "#ECEEF5",
  
  // UI Elements
  white: "#FFFFFF",
  black: "#000000",
  transparent: "transparent",
};

export const STYLES = {
  // Border Styles
  border: {
    solid: `2px solid ${TOKENS.border}`,
    dashed: `2px dashed ${TOKENS.border}`,
    light: `1px solid ${TOKENS.grid}`,
  },
  
  // Border Radius
  radius: {
    small: "6px",
    medium: "8px",
    large: "12px",
    pill: "999px",
  },
  
  // Spacing
  spacing: {
    xs: "4px",
    sm: "6px",
    md: "8px",
    lg: "12px",
    xl: "16px",
    xxl: "24px",
  },
  
  // Typography
  fontSize: {
    xs: "10px",
    sm: "12px",
    base: "14px",
    lg: "16px",
    xl: "18px",
  },
  
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  
  // Shadows (minimal for neubrutalism)
  shadow: {
    none: "none",
    sm: "2px 2px 0px rgba(0,0,0,0.1)",
    md: "3px 3px 0px rgba(0,0,0,0.15)",
    lg: "4px 4px 0px rgba(0,0,0,0.2)",
  },
  
  // Transitions
  transition: {
    fast: "all 0.15s ease",
    base: "all 0.2s ease",
    slow: "all 0.3s ease",
  },
};

// Component-specific styles
export const COMPONENTS = {
  button: {
    base: {
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.medium,
      padding: `${STYLES.spacing.xs} ${STYLES.spacing.lg}`,
      fontSize: STYLES.fontSize.base,
      fontWeight: STYLES.fontWeight.medium,
      background: TOKENS.white,
      color: TOKENS.text,
      cursor: "pointer",
      transition: STYLES.transition.base,
      outline: "none",
    },
    hover: {
      transform: "translateY(-1px)",
      boxShadow: STYLES.shadow.sm,
    },
    active: {
      transform: "translateY(0)",
      boxShadow: STYLES.shadow.none,
    },
    disabled: {
      opacity: 0.5,
      cursor: "not-allowed",
    },
    primary: {
      background: TOKENS.info,
      color: TOKENS.white,
    },
    success: {
      background: TOKENS.ok,
      color: TOKENS.white,
    },
    warning: {
      background: TOKENS.warning,
      color: TOKENS.white,
    },
  },
  
  input: {
    base: {
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.medium,
      padding: `${STYLES.spacing.md} ${STYLES.spacing.lg}`,
      fontSize: STYLES.fontSize.base,
      background: TOKENS.white,
      color: TOKENS.text,
      outline: "none",
      transition: STYLES.transition.base,
    },
    focus: {
      borderColor: TOKENS.info,
      boxShadow: `0 0 0 3px ${TOKENS.info}33`,
    },
    disabled: {
      background: TOKENS.chip,
      color: TOKENS.muted,
      cursor: "not-allowed",
    },
  },
  
  card: {
    base: {
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      background: TOKENS.white,
      overflow: "hidden",
    },
    header: {
      padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
      borderBottom: STYLES.border.solid,
      fontWeight: STYLES.fontWeight.semibold,
    },
    body: {
      padding: `${STYLES.spacing.md} ${STYLES.spacing.lg}`,
    },
    footer: {
      padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
      borderTop: STYLES.border.light,
      fontSize: STYLES.fontSize.sm,
      color: TOKENS.muted,
    },
  },
  
  badge: {
    base: {
      display: "inline-flex",
      alignItems: "center",
      gap: STYLES.spacing.xs,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.pill,
      padding: `2px ${STYLES.spacing.md}`,
      fontSize: STYLES.fontSize.sm,
      fontWeight: STYLES.fontWeight.medium,
    },
    default: {
      background: TOKENS.chip,
      color: TOKENS.text,
    },
    success: {
      background: TOKENS.approved,
      color: TOKENS.text,
    },
    warning: {
      background: TOKENS.awaitingApproval,
      color: TOKENS.text,
    },
    error: {
      background: TOKENS.changesRequested,
      color: TOKENS.text,
    },
    info: {
      background: TOKENS.processBody,
      color: TOKENS.text,
    },
  },
  
  sidebar: {
    base: {
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      background: TOKENS.white,
      overflow: "hidden",
    },
    header: {
      borderBottom: STYLES.border.solid,
      padding: `${STYLES.spacing.md} ${STYLES.spacing.lg}`,
      background: TOKENS.chip,
      fontWeight: STYLES.fontWeight.semibold,
    },
    item: {
      display: "flex",
      alignItems: "center",
      gap: STYLES.spacing.md,
      padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.medium,
      marginBottom: STYLES.spacing.md,
      cursor: "pointer",
      transition: STYLES.transition.base,
    },
    itemHover: {
      transform: "translateX(2px)",
      background: TOKENS.chip,
    },
  },
  
  message: {
    base: {
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      overflow: "hidden",
      background: TOKENS.white,
      width: "100%",
      maxWidth: "440px",
    },
    dashed: {
      border: STYLES.border.dashed,
    },
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
      fontWeight: STYLES.fontWeight.semibold,
      fontSize: STYLES.fontSize.sm,
    },
    body: {
      padding: `${STYLES.spacing.md} ${STYLES.spacing.lg}`,
      fontSize: STYLES.fontSize.base,
      lineHeight: "1.4",
    },
    footer: {
      padding: `${STYLES.spacing.sm} ${STYLES.spacing.md}`,
      fontSize: STYLES.fontSize.xs,
      color: TOKENS.muted,
    },
  },
  
  canvas: {
    base: {
      position: "relative" as const,
      flex: 1,
      border: STYLES.border.solid,
      borderRadius: STYLES.radius.large,
      overflow: "hidden",
      background: TOKENS.bg,
    },
    grid: {
      position: "absolute" as const,
      inset: 0,
      backgroundImage: `
        linear-gradient(0deg, ${TOKENS.grid} 1px, transparent 1px),
        linear-gradient(90deg, ${TOKENS.grid} 1px, transparent 1px)
      `,
      backgroundSize: "16px 16px",
      backgroundPosition: "center",
    },
  },
};

// Animation keyframes CSS
export const ANIMATIONS = `
  @keyframes dash {
    to { stroke-dashoffset: -1000; }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  @keyframes slideIn {
    from { transform: translateX(-10px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
  }
  
  .poly-run { 
    stroke-dasharray: 8 6; 
    animation: dash 2.5s linear infinite; 
  }
  .poly-await { 
    stroke-dasharray: 2 8; 
  }
  .poly-change { 
    stroke-dasharray: 10 6; 
  }
  .animate-spin {
    animation: spin 1s linear infinite;
  }
  .animate-pulse {
    animation: pulse 2s ease-in-out infinite;
  }
  .animate-slide-in {
    animation: slideIn 0.3s ease-out;
  }
`;

// Helper function to create inline styles
export const createStyle = (styles: Record<string, any>) => styles;

// Status indicator helper
export const getStatusColor = (status?: string) => {
  switch (status) {
    case "running": return TOKENS.info;
    case "awaiting_approval": return TOKENS.warning;
    case "approved": return TOKENS.ok;
    case "changes_requested": return TOKENS.warning;
    case "error": return TOKENS.error;
    default: return TOKENS.muted;
  }
};

// Role style helper
export const getRoleStyle = (role: string) => {
  switch (role) {
    case "user":
      return {
        header: TOKENS.userHeader,
        body: TOKENS.userBody,
        icon: "👤",
        dash: false,
      };
    case "system":
      return {
        header: TOKENS.systemHeader,
        body: TOKENS.systemBody,
        icon: "▣",
        dash: false,
      };
    case "process":
      return {
        header: TOKENS.processHeader,
        body: TOKENS.processBody,
        icon: "⚙️",
        dash: true,
      };
    default:
      return {
        header: TOKENS.chip,
        body: TOKENS.white,
        icon: "◯",
        dash: false,
      };
  }
};

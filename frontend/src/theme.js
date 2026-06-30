import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary:   { main: '#6366f1', light: '#818cf8', dark: '#4f46e5' },
    secondary: { main: '#8b5cf6', light: '#a78bfa', dark: '#7c3aed' },
    success:   { main: '#10b981', light: '#34d399', dark: '#059669' },
    warning:   { main: '#f59e0b', light: '#fbbf24', dark: '#d97706' },
    error:     { main: '#ef4444', light: '#f87171', dark: '#dc2626' },
    info:      { main: '#06b6d4', light: '#22d3ee', dark: '#0891b2' },
    background: {
      default: '#0a0e1a',
      paper:   '#0f1629',
    },
    divider: 'rgba(99,102,241,0.12)',
    text: {
      primary:   '#e2e8f0',
      secondary: '#94a3b8',
      disabled:  '#475569',
    },
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    h1: { fontWeight: 800, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.015em' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em' },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    body1: { lineHeight: 1.7 },
    body2: { lineHeight: 1.6 },
    button: { fontWeight: 600, letterSpacing: '0.02em' },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: { body: { scrollbarWidth: 'thin' } },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
          padding: '8px 20px',
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
          boxShadow: '0 4px 15px rgba(99,102,241,0.35)',
          '&:hover': {
            background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
            boxShadow: '0 6px 20px rgba(99,102,241,0.45)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(135deg, rgba(15,22,41,0.95) 0%, rgba(17,25,46,0.95) 100%)',
          border: '1px solid rgba(99,102,241,0.1)',
          backdropFilter: 'blur(20px)',
          transition: 'border-color 0.2s, box-shadow 0.2s',
          '&:hover': {
            borderColor: 'rgba(99,102,241,0.3)',
            boxShadow: '0 8px 32px rgba(99,102,241,0.15)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'rgba(15,22,41,0.95)',
          border: '1px solid rgba(99,102,241,0.1)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, borderRadius: 8 },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 4, height: 6 },
        bar: { borderRadius: 4 },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '& fieldset': { borderColor: 'rgba(99,102,241,0.2)' },
            '&:hover fieldset': { borderColor: 'rgba(99,102,241,0.4)' },
            '&.Mui-focused fieldset': { borderColor: '#6366f1' },
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          background: 'rgba(99,102,241,0.08)',
          fontWeight: 700,
          color: '#94a3b8',
          fontSize: '0.75rem',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        },
        body: { borderBottom: '1px solid rgba(99,102,241,0.06)' },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: '#0f1629',
          borderLeft: '1px solid rgba(99,102,241,0.15)',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 10, border: '1px solid' },
      },
    },
  },
});

export default theme;

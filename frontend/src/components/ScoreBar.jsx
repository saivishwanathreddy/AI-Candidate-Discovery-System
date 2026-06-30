import { Box, Tooltip, LinearProgress, Typography } from '@mui/material';

/**
 * Renders a compact score bar with label and numeric value.
 * value: 0.0 – 1.0
 */
export function ScoreBar({ label, value = 0, color = 'primary', compact = false }) {
  const pct = Math.round((value || 0) * 100);
  const barColor = scoreColor(value);

  return (
    <Box sx={{ mb: compact ? 0.5 : 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.4 }}>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>
          {label}
        </Typography>
        <Typography variant="caption" sx={{ color: barColor, fontWeight: 700 }}>
          {pct}%
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={pct}
        sx={{
          height: compact ? 4 : 6,
          borderRadius: 3,
          backgroundColor: 'rgba(255,255,255,0.06)',
          '& .MuiLinearProgress-bar': { backgroundColor: barColor },
        }}
      />
    </Box>
  );
}

/**
 * Returns a color string based on score value.
 */
export function scoreColor(value = 0) {
  if (value >= 0.75) return '#10b981'; // green
  if (value >= 0.55) return '#6366f1'; // indigo
  if (value >= 0.35) return '#f59e0b'; // amber
  return '#ef4444';                    // red
}

/**
 * Inline badge showing a percentage score.
 */
export function ScoreBadge({ value = 0, size = 'small' }) {
  const pct = Math.round((value || 0) * 100);
  const color = scoreColor(value);
  return (
    <Tooltip title={`Score: ${(value || 0).toFixed(4)}`} arrow>
      <Box
        component="span"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          px: size === 'large' ? 1.5 : 1,
          py: size === 'large' ? 0.6 : 0.3,
          borderRadius: 2,
          fontSize: size === 'large' ? '0.85rem' : '0.72rem',
          fontWeight: 700,
          color,
          background: `${color}18`,
          border: `1px solid ${color}30`,
          letterSpacing: '0.03em',
          cursor: 'default',
          transition: 'all 0.2s',
          '&:hover': { background: `${color}28` },
        }}
      >
        {pct}%
      </Box>
    </Tooltip>
  );
}

/**
 * Rank badge (1, 2, 3 get gold/silver/bronze, rest get plain).
 */
export function RankBadge({ rank }) {
  const medals = { 1: '#fbbf24', 2: '#9ca3af', 3: '#cd7c2c' };
  const color = medals[rank] || '#6366f1';
  return (
    <Box
      sx={{
        width: 32, height: 32,
        borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: rank <= 3 ? `${color}20` : 'rgba(99,102,241,0.1)',
        border: `2px solid ${color}60`,
        color,
        fontSize: '0.78rem',
        fontWeight: 800,
      }}
    >
      {rank}
    </Box>
  );
}

/**
 * Pipeline step indicator used on Dashboard.
 */
export function StepCard({ icon, title, subtitle, done, active, onClick }) {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 2.5,
        borderRadius: 3,
        border: '1px solid',
        borderColor: done
          ? 'rgba(16,185,129,0.4)'
          : active
          ? 'rgba(99,102,241,0.5)'
          : 'rgba(99,102,241,0.1)',
        background: done
          ? 'rgba(16,185,129,0.06)'
          : active
          ? 'rgba(99,102,241,0.08)'
          : 'rgba(15,22,41,0.6)',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s',
        '&:hover': onClick ? { borderColor: 'rgba(99,102,241,0.5)', transform: 'translateY(-2px)' } : {},
        display: 'flex',
        alignItems: 'center',
        gap: 2,
      }}
    >
      <Box sx={{ fontSize: 28 }}>{icon}</Box>
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 600, color: done ? '#10b981' : 'text.primary' }}>
          {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
      </Box>
    </Box>
  );
}

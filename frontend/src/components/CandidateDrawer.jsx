import {
  Drawer, Box, Typography, IconButton, Chip, Divider,
  CircularProgress, Alert, Stack, Tooltip, Avatar
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonIcon from '@mui/icons-material/Person';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import { ScoreBar, ScoreBadge, RankBadge, scoreColor } from './ScoreBar';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip as RTooltip } from 'recharts';

export default function CandidateDrawer({ open, candidate, onClose }) {
  if (!candidate) return null;

  const {
    rank, candidate_id, name, current_title, current_company,
    location, years_of_experience, score, reasoning,
    score_breakdown, explanations, features,
  } = candidate;

  const sb = score_breakdown || {};
  const tech = features?.technical || {};
  const exp = features?.experience || {};
  const beh = features?.behavior || {};
  const trust = features?.trust || {};
  const risk = features?.risk || {};

  const radarData = [
    { subject: 'Semantic',   value: Math.round((sb.semantic || 0) * 100) },
    { subject: 'Technical',  value: Math.round((sb.technical || 0) * 100) },
    { subject: 'Experience', value: Math.round((sb.experience || 0) * 100) },
    { subject: 'Behavior',   value: Math.round((sb.behavior || 0) * 100) },
    { subject: 'Trust',      value: Math.round((sb.trust || 0) * 100) },
  ];

  const positiveNotes = (explanations || []).filter(n => n.sentiment === 'positive');
  const negativeNotes = (explanations || []).filter(n => n.sentiment === 'negative');
  const neutralNotes  = (explanations || []).filter(n => n.sentiment === 'neutral');

  const initials = name
    ? name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : '?';

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{ sx: { width: { xs: '100%', sm: 520 }, overflowX: 'hidden' } }}
    >
      {/* Header */}
      <Box sx={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(139,92,246,0.1) 100%)',
        borderBottom: '1px solid rgba(99,102,241,0.2)',
        p: 3, pb: 2,
      }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Avatar
              sx={{
                width: 56, height: 56,
                background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                fontSize: '1.1rem', fontWeight: 700,
              }}
            >
              {initials}
            </Avatar>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <RankBadge rank={rank} />
                <ScoreBadge value={score} size="large" />
              </Box>
              <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.2 }}>
                {name || candidate_id}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {current_title}{current_company ? ` · ${current_company}` : ''}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small" sx={{ color: 'text.secondary' }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 0.5 }}>
          {location && <Chip label={`📍 ${location}`} size="small" variant="outlined" sx={{ borderColor: 'rgba(99,102,241,0.3)' }} />}
          {years_of_experience > 0 && <Chip label={`${years_of_experience}y exp`} size="small" variant="outlined" sx={{ borderColor: 'rgba(99,102,241,0.3)' }} />}
          <Chip label={candidate_id} size="small" sx={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8', fontSize: '0.68rem' }} />
        </Stack>
      </Box>

      <Box sx={{ p: 3, overflowY: 'auto', flex: 1 }}>

        {/* Radar Chart */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
            Score Radar
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData} outerRadius={70}>
              <PolarGrid stroke="rgba(99,102,241,0.15)" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <Radar dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.25} strokeWidth={2} />
              <RTooltip contentStyle={{ background: '#0f1629', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8 }} formatter={(v) => [`${v}%`]} />
            </RadarChart>
          </ResponsiveContainer>
        </Box>

        <Divider sx={{ mb: 3, borderColor: 'rgba(99,102,241,0.1)' }} />

        {/* Score Breakdown */}
        <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
          Score Breakdown
        </Typography>
        <ScoreBar label="Semantic Match"  value={sb.semantic}   compact />
        <ScoreBar label="Technical"       value={sb.technical}  compact />
        <ScoreBar label="Experience"      value={sb.experience} compact />
        <ScoreBar label="Behavior"        value={sb.behavior}   compact />
        <ScoreBar label="Trust"           value={sb.trust}      compact />
        {sb.risk_penalty > 0 && (
          <Box sx={{ mt: 1, p: 1.5, borderRadius: 2, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
            <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 600 }}>
              ⚠ Risk Penalty: -{Math.round(sb.risk_penalty * 100)}%
            </Typography>
          </Box>
        )}

        <Divider sx={{ my: 3, borderColor: 'rgba(99,102,241,0.1)' }} />

        {/* Skill match */}
        {features && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
              Skill Match
            </Typography>
            {tech.matched_required_skill_names?.length > 0 && (
              <Box sx={{ mb: 1 }}>
                <Typography variant="caption" sx={{ color: '#10b981', fontWeight: 600, display: 'block', mb: 0.5 }}>
                  ✓ Matched Required
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {tech.matched_required_skill_names.map(s => (
                    <Chip key={s} label={s} size="small" sx={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)', fontSize: '0.7rem' }} />
                  ))}
                </Box>
              </Box>
            )}
            {tech.unmatched_required_skill_names?.length > 0 && (
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 600, display: 'block', mb: 0.5 }}>
                  ✗ Missing Required
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {tech.unmatched_required_skill_names.map(s => (
                    <Chip key={s} label={s} size="small" sx={{ background: 'rgba(239,68,68,0.08)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.25)', fontSize: '0.7rem' }} />
                  ))}
                </Box>
              </Box>
            )}
            {tech.matched_preferred_skill_names?.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" sx={{ color: '#6366f1', fontWeight: 600, display: 'block', mb: 0.5 }}>
                  ✓ Preferred
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {tech.matched_preferred_skill_names.map(s => (
                    <Chip key={s} label={s} size="small" sx={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.25)', fontSize: '0.7rem' }} />
                  ))}
                </Box>
              </Box>
            )}
            <Divider sx={{ my: 3, borderColor: 'rgba(99,102,241,0.1)' }} />
          </>
        )}

        {/* Strengths */}
        {positiveNotes.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: '#10b981', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
              ✓ Strengths
            </Typography>
            <Stack spacing={0.75} sx={{ mb: 2 }}>
              {positiveNotes.map((n, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                  <TrendingUpIcon sx={{ fontSize: 14, color: '#10b981', mt: 0.3, flexShrink: 0 }} />
                  <Typography variant="body2" sx={{ color: 'text.primary', fontSize: '0.82rem', lineHeight: 1.5 }}>
                    {n.message}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </>
        )}

        {/* Weaknesses */}
        {negativeNotes.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: '#ef4444', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
              ✗ Concerns
            </Typography>
            <Stack spacing={0.75} sx={{ mb: 2 }}>
              {negativeNotes.map((n, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                  <TrendingDownIcon sx={{ fontSize: 14, color: '#ef4444', mt: 0.3, flexShrink: 0 }} />
                  <Typography variant="body2" sx={{ color: 'text.primary', fontSize: '0.82rem', lineHeight: 1.5 }}>
                    {n.message}
                  </Typography>
                </Box>
              ))}
            </Stack>
          </>
        )}

        {/* Neutral */}
        {neutralNotes.length > 0 && (
          <>
            <Typography variant="subtitle2" sx={{ mb: 1.5, color: '#f59e0b', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
              ℹ Notes
            </Typography>
            <Stack spacing={0.75} sx={{ mb: 2 }}>
              {neutralNotes.map((n, i) => (
                <Typography key={i} variant="body2" sx={{ color: 'text.secondary', fontSize: '0.82rem', lineHeight: 1.5 }}>
                  • {n.message}
                </Typography>
              ))}
            </Stack>
          </>
        )}

        <Divider sx={{ my: 3, borderColor: 'rgba(99,102,241,0.1)' }} />

        {/* Recruiter Summary */}
        <Typography variant="subtitle2" sx={{ mb: 1.5, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.72rem', letterSpacing: '0.08em' }}>
          Recruiter Summary
        </Typography>
        <Box sx={{
          p: 2, borderRadius: 2,
          background: 'rgba(99,102,241,0.06)',
          border: '1px solid rgba(99,102,241,0.15)',
        }}>
          <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.7, fontStyle: 'italic' }}>
            "{reasoning}"
          </Typography>
        </Box>

        {/* Risk flags */}
        {risk?.risk_flags?.length > 0 && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
              Risk Flags
            </Typography>
            {risk.risk_flags.map((f, i) => (
              <Typography key={i} variant="caption" display="block">• {f}</Typography>
            ))}
          </Alert>
        )}
      </Box>
    </Drawer>
  );
}

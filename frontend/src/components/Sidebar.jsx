import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon,
  ListItemText, Toolbar, Typography, Chip, Divider, Tooltip } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import WorkIcon from '@mui/icons-material/Work';
import GroupIcon from '@mui/icons-material/Group';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import LeaderboardIcon from '@mui/icons-material/Leaderboard';
import { useApp } from '../context/AppContext';

const DRAWER_WIDTH = 240;

const navItems = [
  { label: 'Dashboard',       path: '/',          icon: <DashboardIcon />,  key: null },
  { label: 'Upload Job',      path: '/upload-job', icon: <WorkIcon />,       key: 'job' },
  { label: 'Upload Dataset',  path: '/upload-candidates', icon: <GroupIcon />, key: 'candidates' },
  { label: 'Analyze',         path: '/analyze',   icon: <AnalyticsIcon />,  key: 'analysis' },
  { label: 'Results',         path: '/results',   icon: <LeaderboardIcon />,key: 'results' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { state } = useApp();
  const { jobInfo, candidateInfo, analysisResult, results } = state;

  const statusMap = {
    job:       !!jobInfo,
    candidates:!!candidateInfo,
    analysis:  !!analysisResult,
    results:   !!results,
  };

  return (
    <Box
      component="nav"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          borderRight: '1px solid rgba(99,102,241,0.12)',
          background: 'linear-gradient(180deg, #0a0e1a 0%, #0f1629 100%)',
        },
      }}
    >
      <Drawer variant="permanent" sx={{ display: { xs: 'none', sm: 'block' } }}>
        {/* Brand */}
        <Box sx={{ px: 2.5, py: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0.5 }}>
            <Box sx={{
              width: 36, height: 36, borderRadius: 2,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.1rem',
            }}>
              🤖
            </Box>
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 800, color: 'text.primary', lineHeight: 1.1 }}>
                AI Candidate
              </Typography>
              <Typography variant="caption" sx={{ color: '#6366f1', fontWeight: 600 }}>
                Discovery System
              </Typography>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ borderColor: 'rgba(99,102,241,0.1)', mb: 1 }} />

        <List sx={{ px: 1.5 }}>
          {navItems.map(({ label, path, icon, key }) => {
            const active = pathname === path;
            const done = key ? statusMap[key] : false;

            return (
              <ListItem key={path} disablePadding sx={{ mb: 0.5 }}>
                <ListItemButton
                  onClick={() => navigate(path)}
                  sx={{
                    borderRadius: 2,
                    py: 1,
                    background: active
                      ? 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))'
                      : 'transparent',
                    border: '1px solid',
                    borderColor: active ? 'rgba(99,102,241,0.4)' : 'transparent',
                    '&:hover': {
                      background: 'rgba(99,102,241,0.1)',
                      borderColor: 'rgba(99,102,241,0.25)',
                    },
                    transition: 'all 0.15s',
                  }}
                >
                  <ListItemIcon sx={{
                    minWidth: 36,
                    color: active ? '#818cf8' : done ? '#10b981' : '#475569',
                  }}>
                    {icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={label}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: active ? 700 : 500,
                      color: active ? '#e2e8f0' : done ? '#10b981' : '#94a3b8',
                    }}
                  />
                  {done && !active && (
                    <Box sx={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
                  )}
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        {/* Pipeline status mini summary */}
        <Box sx={{ mt: 'auto', p: 2, mx: 1.5, mb: 2, borderRadius: 2, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.1)' }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600, display: 'block', mb: 1, textTransform: 'uppercase', letterSpacing: '0.06em', fontSize: '0.68rem' }}>
            Pipeline Status
          </Typography>
          {[
            { label: 'Job',        done: !!jobInfo,        detail: jobInfo?.job_title },
            { label: 'Candidates', done: !!candidateInfo,  detail: candidateInfo ? `${candidateInfo.valid_candidates} loaded` : null },
            { label: 'Analyzed',   done: !!analysisResult, detail: analysisResult ? `${analysisResult.ranked_count} ranked` : null },
          ].map(({ label, done, detail }) => (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
              <Box sx={{ width: 6, height: 6, borderRadius: '50%', background: done ? '#10b981' : '#334155', flexShrink: 0 }} />
              <Typography variant="caption" sx={{ color: done ? '#10b981' : '#475569', fontWeight: 500, fontSize: '0.72rem' }}>
                {label}
              </Typography>
              {done && detail && (
                <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.68rem', ml: 'auto', maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {detail}
                </Typography>
              )}
            </Box>
          ))}
        </Box>
      </Drawer>
    </Box>
  );
}

export { DRAWER_WIDTH };

import { useEffect, useState } from 'react';
import {
  Box, Grid, Typography, Card, CardContent, Button,
  Chip, Skeleton, Alert, LinearProgress, Stack
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import WorkIcon from '@mui/icons-material/Work';
import GroupIcon from '@mui/icons-material/Group';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import LeaderboardIcon from '@mui/icons-material/Leaderboard';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { useApp } from '../context/AppContext';
import { fetchHealth } from '../api';
import { ScoreBadge } from '../components/ScoreBar';

export default function Dashboard() {
  const navigate = useNavigate();
  const { state, refreshHealth } = useApp();
  const { jobInfo, candidateInfo, analysisResult, results } = state;
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  const steps = [
    {
      icon: <WorkIcon sx={{ fontSize: 32, color: jobInfo ? '#10b981' : '#6366f1' }} />,
      title: 'Upload Job Description',
      desc: jobInfo
        ? `✓ ${jobInfo.job_title} @ ${jobInfo.company}`
        : 'Upload your .docx JD or use the default',
      done: !!jobInfo,
      path: '/upload-job',
      detail: jobInfo ? `${jobInfo.required_skills} required skills` : null,
    },
    {
      icon: <GroupIcon sx={{ fontSize: 32, color: candidateInfo ? '#10b981' : '#6366f1' }} />,
      title: 'Upload Candidate Dataset',
      desc: candidateInfo
        ? `✓ ${candidateInfo.valid_candidates.toLocaleString()} candidates loaded`
        : 'Upload .jsonl / .json or use the 50-sample',
      done: !!candidateInfo,
      path: '/upload-candidates',
      detail: candidateInfo ? candidateInfo.source : null,
    },
    {
      icon: <AnalyticsIcon sx={{ fontSize: 32, color: analysisResult ? '#10b981' : '#6366f1' }} />,
      title: 'Run Analysis',
      desc: analysisResult
        ? `✓ ${analysisResult.ranked_count} candidates ranked in ${analysisResult.processing_time_seconds}s`
        : 'Feature engineering + semantic matching + ranking',
      done: !!analysisResult,
      path: '/analyze',
      detail: null,
    },
    {
      icon: <LeaderboardIcon sx={{ fontSize: 32, color: results ? '#10b981' : '#6366f1' }} />,
      title: 'View Results',
      desc: results
        ? `${results.total_ranked} ranked candidates ready`
        : 'Browse ranked shortlist with explainability',
      done: !!results,
      path: '/results',
      detail: null,
    },
  ];

  const completedSteps = steps.filter(s => s.done).length;
  const nextStep = steps.find(s => !s.done);

  return (
    <Box>
      {/* Hero */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>
          <span className="gradient-text">AI Candidate Discovery</span>
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Semantic + multi-dimensional ranking pipeline for intelligent talent acquisition
        </Typography>

        {/* Overall progress */}
        <Box sx={{ mb: 1, display: 'flex', justifyContent: 'space-between' }}>
          <Typography variant="caption" color="text.secondary">
            Pipeline progress
          </Typography>
          <Typography variant="caption" sx={{ color: '#6366f1', fontWeight: 700 }}>
            {completedSteps}/{steps.length} steps
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={(completedSteps / steps.length) * 100}
          sx={{
            height: 6, borderRadius: 3,
            backgroundColor: 'rgba(99,102,241,0.1)',
            '& .MuiLinearProgress-bar': {
              background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
            },
          }}
        />
      </Box>

      {/* Backend health banner */}
      {!loading && health && (
        <Alert
          severity={health.status === 'ok' ? 'success' : 'error'}
          sx={{ mb: 3 }}
          icon={<CheckCircleIcon />}
        >
          Backend connected · Engine v{health.engine_version}
          {health.job_loaded && ' · Job loaded'}
          {health.candidates_loaded > 0 && ` · ${health.candidates_loaded} candidates`}
          {health.results_available && ' · Results ready'}
        </Alert>
      )}
      {!loading && !health && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Cannot reach backend at http://localhost:8000 — start with{' '}
          <code>uvicorn backend.main:app --reload</code>
        </Alert>
      )}

      {/* Pipeline Steps */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {steps.map((step, i) => (
          <Grid item xs={12} sm={6} key={i}>
            <Card
              onClick={() => navigate(step.path)}
              sx={{
                cursor: 'pointer',
                borderColor: step.done ? 'rgba(16,185,129,0.3)' : 'rgba(99,102,241,0.12)',
                '&:hover': {
                  borderColor: step.done ? 'rgba(16,185,129,0.6)' : 'rgba(99,102,241,0.4)',
                  transform: 'translateY(-2px)',
                },
                transition: 'all 0.2s',
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {step.done && (
                <Box sx={{
                  position: 'absolute', top: 0, left: 0, right: 0, height: 3,
                  background: 'linear-gradient(90deg, #10b981, #06b6d4)',
                }} />
              )}
              <CardContent sx={{ p: 2.5 }}>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
                  <Box sx={{
                    p: 1.2, borderRadius: 2,
                    background: step.done ? 'rgba(16,185,129,0.1)' : 'rgba(99,102,241,0.1)',
                  }}>
                    {step.icon}
                  </Box>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography variant="body1" sx={{ fontWeight: 700 }}>
                        {i + 1}. {step.title}
                      </Typography>
                      {step.done && (
                        <CheckCircleIcon sx={{ fontSize: 16, color: '#10b981' }} />
                      )}
                    </Box>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {step.desc}
                    </Typography>
                    {step.detail && (
                      <Chip
                        label={step.detail}
                        size="small"
                        sx={{ mt: 1, background: 'rgba(99,102,241,0.1)', color: '#818cf8', fontSize: '0.68rem' }}
                      />
                    )}
                  </Box>
                  <ArrowForwardIcon sx={{ color: '#475569', mt: 0.5 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Quick stats if analysis done */}
      {analysisResult && (
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
            Analysis Summary
          </Typography>
          <Grid container spacing={2}>
            {[
              { label: 'Total Evaluated',  value: analysisResult.total_candidates_evaluated?.toLocaleString(), color: '#6366f1' },
              { label: 'Valid Candidates', value: analysisResult.valid_candidates?.toLocaleString(), color: '#8b5cf6' },
              { label: 'Ranked',           value: analysisResult.ranked_count, color: '#10b981' },
              { label: 'Processing Time',  value: `${analysisResult.processing_time_seconds}s`, color: '#06b6d4' },
            ].map(({ label, value, color }) => (
              <Grid item xs={6} sm={3} key={label}>
                <Card>
                  <CardContent sx={{ textAlign: 'center', py: 2 }}>
                    <Typography sx={{ fontSize: '1.75rem', fontWeight: 800, color }}>
                      {value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {label}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Next action CTA */}
      {nextStep && (
        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Button
            variant="contained"
            size="large"
            endIcon={<ArrowForwardIcon />}
            onClick={() => navigate(nextStep.path)}
          >
            Next: {nextStep.title}
          </Button>
        </Box>
      )}
    </Box>
  );
}

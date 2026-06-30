import { useState } from 'react';
import {
  Box, Typography, Card, CardContent, Button, Alert,
  LinearProgress, Slider, Grid, Chip, Stack, Stepper,
  Step, StepLabel, StepContent, TextField
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import { useApp } from '../context/AppContext';
import { runAnalysis } from '../api';

const PIPELINE_STEPS = [
  { label: 'Feature Engineering',     desc: 'Extracting 50+ features per candidate' },
  { label: 'Semantic Matching',       desc: 'Embedding + cosine similarity' },
  { label: 'Hybrid Ranking',          desc: 'Weighted multi-dimension scoring' },
  { label: 'Explainability',          desc: 'Generating human-readable notes' },
];

export default function Analyze() {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { state, setAnalysis } = useApp();
  const { jobInfo, candidateInfo, analysisResult } = state;

  const [weights, setWeights] = useState({
    weight_semantic: 0.35,
    weight_technical: 0.30,
    weight_experience: 0.15,
    weight_behavior: 0.12,
    weight_trust: 0.08,
  });
  const [topK, setTopK] = useState(100);
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(-1);
  const [error, setError] = useState(null);

  const canRun = !!jobInfo && !!candidateInfo;

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    setActiveStep(0);

    // Simulate step progression (backend runs synchronously, so we animate)
    const stepDelay = (ms) => new Promise(r => setTimeout(r, ms));
    const advanceSteps = async () => {
      for (let i = 1; i < PIPELINE_STEPS.length; i++) {
        await stepDelay(1200);
        setActiveStep(i);
      }
    };

    try {
      const [data] = await Promise.all([
        runAnalysis({ ...weights, top_k: topK }),
        advanceSteps(),
      ]);
      setActiveStep(PIPELINE_STEPS.length); // all done
      setAnalysis(data);
      enqueueSnackbar(`Analysis complete! ${data.ranked_count} candidates ranked.`, { variant: 'success' });
    } catch (err) {
      setError(err.userMessage || 'Analysis failed.');
      enqueueSnackbar('Analysis failed.', { variant: 'error' });
      setActiveStep(-1);
    } finally {
      setLoading(false);
    }
  };

  const wSum = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Run Analysis</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Configure scoring weights and launch the full AI pipeline.
      </Typography>

      {/* Prerequisites check */}
      {!canRun && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {!jobInfo && !candidateInfo
            ? 'Upload a job description AND candidate dataset first.'
            : !jobInfo
            ? 'Upload a job description first (Step 1).'
            : 'Upload a candidate dataset first (Step 2).'}
        </Alert>
      )}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Config */}
        <Grid item xs={12} md={5}>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Scoring Weights</Typography>

              {[
                { key: 'weight_semantic',   label: 'Semantic',   color: '#6366f1' },
                { key: 'weight_technical',  label: 'Technical',  color: '#8b5cf6' },
                { key: 'weight_experience', label: 'Experience', color: '#06b6d4' },
                { key: 'weight_behavior',   label: 'Behavior',   color: '#10b981' },
                { key: 'weight_trust',      label: 'Trust',      color: '#f59e0b' },
              ].map(({ key, label, color }) => (
                <Box key={key} sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{label}</Typography>
                    <Typography variant="caption" sx={{ color, fontWeight: 700 }}>
                      {(weights[key] * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Slider
                    value={weights[key]}
                    min={0} max={1} step={0.01}
                    onChange={(_, v) => setWeights(w => ({ ...w, [key]: v }))}
                    disabled={loading}
                    sx={{ color, '& .MuiSlider-thumb': { width: 14, height: 14 } }}
                  />
                </Box>
              ))}

              <Box sx={{ p: 1.5, borderRadius: 2, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)' }}>
                <Typography variant="caption" color="text.secondary">
                  Weights are auto-normalised by the backend. Sum: {(wSum).toFixed(2)}
                </Typography>
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>Top K candidates</Typography>
                <TextField
                  type="number"
                  size="small"
                  value={topK}
                  onChange={e => setTopK(Math.min(100, Math.max(1, parseInt(e.target.value) || 1)))}
                  inputProps={{ min: 1, max: 100 }}
                  disabled={loading}
                  fullWidth
                  helperText="1 – 100"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Pipeline status */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Pipeline Stages</Typography>

              <Stepper activeStep={activeStep} orientation="vertical">
                {PIPELINE_STEPS.map((step, i) => (
                  <Step key={step.label} completed={activeStep > i}>
                    <StepLabel
                      StepIconProps={{
                        sx: {
                          color: activeStep > i ? '#10b981 !important' : undefined,
                          '&.Mui-active': { color: '#6366f1 !important' },
                        },
                      }}
                    >
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>{step.label}</Typography>
                    </StepLabel>
                    <StepContent>
                      <Typography variant="caption" color="text.secondary">{step.desc}</Typography>
                      {activeStep === i && loading && (
                        <LinearProgress sx={{ mt: 1, width: 200 }} />
                      )}
                    </StepContent>
                  </Step>
                ))}
              </Stepper>

              {activeStep === PIPELINE_STEPS.length && analysisResult && (
                <Box sx={{ mt: 2, p: 2, borderRadius: 2, background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <CheckCircleIcon sx={{ color: '#10b981' }} />
                    <Typography variant="body2" sx={{ fontWeight: 700, color: '#10b981' }}>
                      Analysis Complete
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
                    <Chip label={`${analysisResult.ranked_count} ranked`} size="small" color="success" />
                    <Chip label={`${analysisResult.processing_time_seconds}s`} size="small" variant="outlined" />
                  </Stack>
                </Box>
              )}

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayArrowIcon />}
                  onClick={handleRun}
                  disabled={!canRun || loading}
                  sx={{ minWidth: 160 }}
                >
                  {loading ? 'Analyzing…' : analysisResult ? 'Re-Analyze' : 'Run Analysis'}
                </Button>
                {analysisResult && (
                  <Button
                    variant="outlined"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate('/results')}
                  >
                    View Results
                  </Button>
                )}
              </Box>

              {canRun && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Job: <strong>{jobInfo.job_title}</strong> &nbsp;·&nbsp;
                    Candidates: <strong>{candidateInfo.valid_candidates.toLocaleString()}</strong>
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

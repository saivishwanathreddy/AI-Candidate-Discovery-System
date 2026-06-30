import { useState, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Button, Alert,
  LinearProgress, Chip, Stack, Divider, TextField,
  FormControlLabel, Switch, Collapse
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import GroupIcon from '@mui/icons-material/Group';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import { useApp } from '../context/AppContext';
import { uploadCandidates } from '../api';

export default function UploadCandidates() {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { setCandidates } = useApp();

  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [maxRecords, setMaxRecords] = useState('');
  const [validate, setValidate] = useState(true);

  const handleFile = (f) => {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['jsonl', 'json'].includes(ext)) {
      setError('Only .jsonl or .json files are accepted.');
      return;
    }
    setFile(f);
    setError(null);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files[0]);
  }, []);

  const doUpload = async (useSample, useDefault) => {
    setLoading(true);
    setError(null);
    try {
      const data = await uploadCandidates({
        file: useDefault || useSample ? null : file,
        useSample,
        maxRecords: maxRecords ? parseInt(maxRecords) : null,
        validate,
      });
      setResult(data);
      setCandidates(data);
      enqueueSnackbar(`${data.valid_candidates.toLocaleString()} candidates loaded!`, { variant: 'success' });
    } catch (err) {
      setError(err.userMessage || 'Upload failed.');
      enqueueSnackbar('Candidate upload failed.', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Upload Candidate Dataset</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Upload a <code>.jsonl</code> or <code>.json</code> file, use the 50-candidate sample, or load the full 100K dataset.
      </Typography>

      {loading && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            Loading candidates — this may take a moment for large datasets…
          </Typography>
        </Box>
      )}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {result ? (
        <Card sx={{ mb: 3, borderColor: 'rgba(16,185,129,0.3) !important' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <CheckCircleIcon sx={{ color: '#10b981', fontSize: 32 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {result.valid_candidates.toLocaleString()} candidates ready
                </Typography>
                <Typography color="text.secondary" variant="caption">{result.source}</Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
              <Chip label={`${result.valid_candidates.toLocaleString()} valid`} size="small" color="success" variant="outlined" />
              {result.invalid_candidates > 0 && (
                <Chip label={`${result.invalid_candidates} skipped`} size="small" color="warning" variant="outlined" />
              )}
            </Stack>
            <Alert severity="success" sx={{ mt: 2 }}>{result.message}</Alert>
            <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
              <Button variant="outlined" onClick={() => { setResult(null); setFile(null); }}>
                Load Different Dataset
              </Button>
              <Button variant="contained" endIcon={<ArrowForwardIcon />} onClick={() => navigate('/analyze')}>
                Next: Run Analysis
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Options row */}
          <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              label="Max records (optional)"
              type="number"
              size="small"
              value={maxRecords}
              onChange={e => setMaxRecords(e.target.value)}
              inputProps={{ min: 1 }}
              sx={{ width: 200 }}
              helperText="Leave empty to load all"
            />
            <FormControlLabel
              control={<Switch checked={validate} onChange={e => setValidate(e.target.checked)} />}
              label={<Typography variant="body2">Schema validation</Typography>}
            />
          </Box>

          {/* Drop zone */}
          <Card
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            sx={{
              mb: 3, cursor: 'pointer',
              borderColor: dragOver ? '#6366f1 !important' : file ? 'rgba(16,185,129,0.4) !important' : 'rgba(99,102,241,0.2) !important',
              borderStyle: 'dashed !important',
              borderWidth: '2px !important',
              background: dragOver ? 'rgba(99,102,241,0.08)' : 'transparent',
              transition: 'all 0.2s',
            }}
            onClick={() => document.getElementById('cand-file-input').click()}
          >
            <CardContent sx={{ textAlign: 'center', py: 5 }}>
              <input
                id="cand-file-input"
                type="file"
                accept=".jsonl,.json"
                style={{ display: 'none' }}
                onChange={e => handleFile(e.target.files[0])}
              />
              {file ? (
                <>
                  <GroupIcon sx={{ fontSize: 48, color: '#10b981', mb: 1 }} />
                  <Typography variant="h6" sx={{ fontWeight: 600, color: '#10b981' }}>{file.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {(file.size / 1024 / 1024).toFixed(2)} MB · Click to change
                  </Typography>
                </>
              ) : (
                <>
                  <UploadFileIcon sx={{ fontSize: 48, color: '#475569', mb: 1 }} />
                  <Typography variant="h6" color="text.secondary">
                    Drop your .jsonl or .json file here or <span style={{ color: '#6366f1' }}>browse</span>
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Supports JSONL (one record per line) or JSON array
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
            <Button
              variant="contained"
              size="large"
              disabled={loading || !file}
              onClick={() => doUpload(false, false)}
            >
              Upload & Load
            </Button>

            <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', sm: 'block' } }} />

            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Or use built-in data:</Typography>
              <Stack direction="row" spacing={1}>
                <Button variant="outlined" size="small" disabled={loading} onClick={() => doUpload(true, false)}>
                  50-Candidate Sample
                </Button>
                <Button variant="outlined" size="small" disabled={loading} onClick={() => doUpload(false, true)}
                  sx={{ borderColor: 'rgba(239,68,68,0.4)', color: '#ef4444' }}>
                  Full 100K Dataset
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                Full dataset load takes ~2 min
              </Typography>
            </Box>
          </Stack>
        </>
      )}
    </Box>
  );
}

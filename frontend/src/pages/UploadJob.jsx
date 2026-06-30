import { useState, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Button, Alert,
  LinearProgress, Chip, Stack, Divider
} from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import WorkIcon from '@mui/icons-material/Work';
import { useNavigate } from 'react-router-dom';
import { useSnackbar } from 'notistack';
import { useApp } from '../context/AppContext';
import { uploadJob } from '../api';

export default function UploadJob() {
  const navigate = useNavigate();
  const { enqueueSnackbar } = useSnackbar();
  const { setJob } = useApp();

  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.docx')) {
      setError('Only .docx files are accepted.');
      return;
    }
    setFile(f);
    setError(null);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleUpload = async (useDefault = false) => {
    setLoading(true);
    setError(null);
    try {
      const data = await uploadJob(useDefault ? null : file);
      setResult(data);
      setJob(data);
      enqueueSnackbar(`Job "${data.job_title}" uploaded successfully!`, { variant: 'success' });
    } catch (err) {
      setError(err.userMessage || 'Upload failed.');
      enqueueSnackbar('Job upload failed.', { variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>Upload Job Description</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Upload a <code>.docx</code> job description file, or use the built-in default (Redrob AI Senior AI Engineer JD).
      </Typography>

      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {result ? (
        /* Success state */
        <Card sx={{ mb: 3, borderColor: 'rgba(16,185,129,0.3) !important' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <CheckCircleIcon sx={{ color: '#10b981', fontSize: 32 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>{result.job_title}</Typography>
                <Typography color="text.secondary">{result.company}</Typography>
              </Box>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
              <Chip label={`${result.required_skills} required skills`} size="small" color="success" variant="outlined" />
              <Chip label={`${result.preferred_skills} preferred skills`} size="small" color="primary" variant="outlined" />
            </Stack>
            <Alert severity="success" sx={{ mt: 2 }}>{result.message}</Alert>
            <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
              <Button variant="outlined" onClick={() => { setResult(null); setFile(null); }}>
                Upload Different JD
              </Button>
              <Button variant="contained" endIcon={<ArrowForwardIcon />} onClick={() => navigate('/upload-candidates')}>
                Next: Upload Candidates
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <>
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
            onClick={() => document.getElementById('jd-file-input').click()}
          >
            <CardContent sx={{ textAlign: 'center', py: 5 }}>
              <input
                id="jd-file-input"
                type="file"
                accept=".docx"
                style={{ display: 'none' }}
                onChange={(e) => handleFile(e.target.files[0])}
              />
              {file ? (
                <>
                  <WorkIcon sx={{ fontSize: 48, color: '#10b981', mb: 1 }} />
                  <Typography variant="h6" sx={{ fontWeight: 600, color: '#10b981' }}>{file.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {(file.size / 1024).toFixed(1)} KB · Click to change
                  </Typography>
                </>
              ) : (
                <>
                  <UploadFileIcon sx={{ fontSize: 48, color: '#475569', mb: 1 }} />
                  <Typography variant="h6" color="text.secondary">
                    Drop your .docx file here or <span style={{ color: '#6366f1' }}>browse</span>
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Supports Microsoft Word .docx format
                  </Typography>
                </>
              )}
            </CardContent>
          </Card>

          <Stack direction="row" spacing={2} alignItems="center">
            <Button
              variant="contained"
              size="large"
              disabled={loading || !file}
              onClick={() => handleUpload(false)}
            >
              Upload & Parse
            </Button>
            <Divider orientation="vertical" flexItem />
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                No file? Use the built-in default JD:
              </Typography>
              <Button
                variant="outlined"
                size="small"
                disabled={loading}
                onClick={() => handleUpload(true)}
              >
                Use Default JD (Redrob AI)
              </Button>
            </Box>
          </Stack>
        </>
      )}
    </Box>
  );
}

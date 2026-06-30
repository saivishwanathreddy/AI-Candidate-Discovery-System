import { useEffect, useState, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, TableSortLabel,
  TablePagination, TextField, InputAdornment, Slider, Alert,
  LinearProgress, Chip, IconButton, Tooltip, Stack, Grid,
  Paper, Button
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import FilterListIcon from '@mui/icons-material/FilterList';
import RefreshIcon from '@mui/icons-material/Refresh';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useSnackbar } from 'notistack';
import { useApp } from '../context/AppContext';
import { fetchResults, fetchCandidate } from '../api';
import { ScoreBadge, RankBadge, ScoreBar, scoreColor } from '../components/ScoreBar';
import CandidateDrawer from '../components/CandidateDrawer';

export default function Results() {
  const { enqueueSnackbar } = useSnackbar();
  const { state, setResults } = useApp();
  const { results: stored, analysisResult } = state;

  const [allCandidates, setAllCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Search / filter / sort
  const [search, setSearch] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [sortField, setSortField] = useState('rank');
  const [sortDir, setSortDir] = useState('asc');

  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Load all pages to support client-side search/sort
      const first = await fetchResults({ page: 1, pageSize: 100, minScore: 0 });
      setResults(first);
      setAllCandidates(first.candidates || []);
    } catch (err) {
      setError(err.userMessage || 'Failed to load results.');
    } finally {
      setLoading(false);
    }
  }, [setResults]);

  useEffect(() => {
    if (analysisResult && !allCandidates.length) loadAll();
    else if (stored?.candidates && !allCandidates.length) {
      setAllCandidates(stored.candidates);
    }
  }, [analysisResult, stored]);

  // ── Client-side filtering + sorting ──────────────────────────────────────
  const filtered = allCandidates
    .filter(c => {
      const q = search.toLowerCase();
      return (
        (c.score || 0) >= minScore &&
        (!q ||
          c.name?.toLowerCase().includes(q) ||
          c.candidate_id?.toLowerCase().includes(q) ||
          c.current_title?.toLowerCase().includes(q) ||
          c.current_company?.toLowerCase().includes(q) ||
          c.location?.toLowerCase().includes(q))
      );
    })
    .sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1;
      if (sortField === 'rank') return mult * (a.rank - b.rank);
      if (sortField === 'name') return mult * (a.name || '').localeCompare(b.name || '');
      const va = a.score_breakdown?.[sortField] ?? a[sortField] ?? 0;
      const vb = b.score_breakdown?.[sortField] ?? b[sortField] ?? 0;
      return mult * (va - vb);
    });

  const paged = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir(field === 'rank' ? 'asc' : 'desc'); }
  };

  const handleOpenCandidate = async (cand) => {
    setSelectedCandidate(cand);
    setDrawerOpen(true);
    if (!cand.features) {
      setDrawerLoading(true);
      try {
        const data = await fetchCandidate(cand.candidate_id);
        setSelectedCandidate(data);
      } catch {
        enqueueSnackbar('Failed to load candidate details.', { variant: 'error' });
      } finally {
        setDrawerLoading(false);
      }
    }
  };

  const SortableCell = ({ field, label }) => (
    <TableCell>
      <TableSortLabel
        active={sortField === field}
        direction={sortField === field ? sortDir : 'asc'}
        onClick={() => handleSort(field)}
        sx={{ '& .MuiTableSortLabel-icon': { color: '#6366f1 !important' } }}
      >
        {label}
      </TableSortLabel>
    </TableCell>
  );

  if (!analysisResult && !stored) {
    return (
      <Box sx={{ textAlign: 'center', py: 10 }}>
        <Typography variant="h6" color="text.secondary">
          No results yet — run analysis first.
        </Typography>
        <Button variant="contained" sx={{ mt: 2 }} onClick={() => window.location.href = '/analyze'}>
          Go to Analyze
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3 }}>
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Ranked Candidates</Typography>
          <Typography color="text.secondary">
            {stored?.job_title && `${stored.job_title} @ ${stored.company} · `}
            {filtered.length} of {allCandidates.length} candidates shown
          </Typography>
        </Box>
        <Tooltip title="Refresh results">
          <IconButton onClick={loadAll} disabled={loading} sx={{ border: '1px solid rgba(99,102,241,0.2)' }}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Stats row */}
      {stored && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[
            { label: 'Evaluated',  value: stored.total_candidates_evaluated?.toLocaleString(), color: '#6366f1' },
            { label: 'Valid',      value: stored.valid_candidates?.toLocaleString(), color: '#8b5cf6' },
            { label: 'Ranked',     value: stored.total_ranked, color: '#10b981' },
            { label: 'Time',       value: `${stored.processing_time_seconds}s`, color: '#06b6d4' },
          ].map(({ label, value, color }) => (
            <Grid item xs={6} sm={3} key={label}>
              <Paper sx={{ p: 2, textAlign: 'center', borderColor: `${color}30 !important` }}>
                <Typography sx={{ fontSize: '1.5rem', fontWeight: 800, color }}>{value}</Typography>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Search + Filter */}
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ p: 2 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
            <TextField
              size="small"
              placeholder="Search name, title, company, location…"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              InputProps={{
                startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#475569' }} /></InputAdornment>,
              }}
              sx={{ flex: 1 }}
            />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, minWidth: 240 }}>
              <FilterListIcon sx={{ color: '#475569', flexShrink: 0 }} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Min score: {Math.round(minScore * 100)}%
                </Typography>
                <Slider
                  value={minScore} min={0} max={1} step={0.01}
                  onChange={(_, v) => { setMinScore(v); setPage(0); }}
                  size="small"
                  sx={{ color: '#6366f1' }}
                />
              </Box>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Table */}
      <Card>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <SortableCell field="rank"       label="Rank" />
                <SortableCell field="name"       label="Candidate" />
                <TableCell>Location</TableCell>
                <TableCell>Exp</TableCell>
                <SortableCell field="score"      label="Final" />
                <SortableCell field="semantic"   label="Semantic" />
                <SortableCell field="technical"  label="Technical" />
                <SortableCell field="experience" label="Experience" />
                <SortableCell field="behavior"   label="Behavior" />
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {paged.map((cand) => (
                <TableRow
                  key={cand.candidate_id}
                  hover
                  onClick={() => handleOpenCandidate(cand)}
                  sx={{
                    cursor: 'pointer',
                    '&:hover': { background: 'rgba(99,102,241,0.05) !important' },
                    borderLeft: `3px solid ${scoreColor(cand.score)}40`,
                  }}
                >
                  <TableCell>
                    <RankBadge rank={cand.rank} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {cand.name || cand.candidate_id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {cand.current_title}
                      {cand.current_company ? ` · ${cand.current_company}` : ''}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">{cand.location || '—'}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {cand.years_of_experience ? `${cand.years_of_experience}y` : '—'}
                    </Typography>
                  </TableCell>
                  <TableCell><ScoreBadge value={cand.score} size="large" /></TableCell>
                  <TableCell><ScoreBadge value={cand.score_breakdown?.semantic} /></TableCell>
                  <TableCell><ScoreBadge value={cand.score_breakdown?.technical} /></TableCell>
                  <TableCell><ScoreBadge value={cand.score_breakdown?.experience} /></TableCell>
                  <TableCell><ScoreBadge value={cand.score_breakdown?.behavior} /></TableCell>
                  <TableCell>
                    <IconButton size="small" sx={{ color: '#475569' }}>
                      <OpenInNewIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {paged.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10} sx={{ textAlign: 'center', py: 6, color: '#475569' }}>
                    No candidates match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={filtered.length}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={e => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
          rowsPerPageOptions={[10, 25, 50, 100]}
          sx={{ borderTop: '1px solid rgba(99,102,241,0.1)' }}
        />
      </Card>

      {/* Candidate Detail Drawer */}
      <CandidateDrawer
        open={drawerOpen}
        candidate={selectedCandidate}
        onClose={() => { setDrawerOpen(false); setSelectedCandidate(null); }}
      />
    </Box>
  );
}

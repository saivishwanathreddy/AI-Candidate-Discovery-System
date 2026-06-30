import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { SnackbarProvider } from 'notistack';
import { Box } from '@mui/material';
import theme from './theme';
import { AppProvider } from './context/AppContext';
import Sidebar, { DRAWER_WIDTH } from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import UploadJob from './pages/UploadJob';
import UploadCandidates from './pages/UploadCandidates';
import Analyze from './pages/Analyze';
import Results from './pages/Results';

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <SnackbarProvider
        maxSnack={4}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        autoHideDuration={4000}
      >
        <AppProvider>
          <BrowserRouter>
            <Box sx={{ display: 'flex', minHeight: '100vh' }}>
              <Sidebar />
              <Box
                component="main"
                sx={{
                  flex: 1,
                  ml: { sm: `${DRAWER_WIDTH}px` },
                  p: { xs: 2, sm: 4 },
                  maxWidth: 1200,
                  minHeight: '100vh',
                }}
              >
                <Routes>
                  <Route path="/"                   element={<Dashboard />} />
                  <Route path="/upload-job"          element={<UploadJob />} />
                  <Route path="/upload-candidates"   element={<UploadCandidates />} />
                  <Route path="/analyze"             element={<Analyze />} />
                  <Route path="/results"             element={<Results />} />
                </Routes>
              </Box>
            </Box>
          </BrowserRouter>
        </AppProvider>
      </SnackbarProvider>
    </ThemeProvider>
  );
}

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AskPage } from './pages/AskPage';
import { HistoryPage } from './pages/HistoryPage';
import { RunDetailPage } from './pages/RunDetailPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { GuidePage } from './pages/GuidePage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<AskPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/history/:runId" element={<RunDetailPage />} />
          <Route path="/evaluation" element={<EvaluationPage />} />
          <Route path="/guide" element={<GuidePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Placeholder } from './pages/Placeholder';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/documents" element={<Placeholder title="Documents" />} />
            <Route path="/workspace/:id" element={<Placeholder title="Workspace" />} />
            <Route path="/chat" element={<Placeholder title="AI Copilot" />} />
            <Route path="/search" element={<Placeholder title="Semantic Search" />} />
            <Route path="/analytics" element={<Placeholder title="Analytics" />} />
            <Route path="/compare" element={<Placeholder title="Compare Documents" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

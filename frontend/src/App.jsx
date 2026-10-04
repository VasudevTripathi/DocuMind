import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { Dashboard } from './pages/Dashboard/Dashboard';
import { Documents } from './pages/Documents/Documents';
import { Landing } from './pages/Landing/Landing';
import { Chat } from './pages/Chat/Chat';
import { Compare } from './pages/Compare/Compare';
import { Analytics } from './pages/Analytics/Analytics';
import { Workspace } from './pages/Workspace/Workspace';
import { Placeholder } from './pages/Placeholder';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/workspace/:id" element={<Workspace />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/search" element={<Placeholder title="Semantic Search" description="Find exact matches and conceptual similarities." />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/calendar" element={<Placeholder title="Calendar" description="Document events and schedules." />} />
            <Route path="/knowledge-base" element={<Placeholder title="Knowledge Base" description="Your connected knowledge sources." />} />
            <Route path="/projects/:id" element={<Placeholder title="Projects" description="Organize your documents by project." />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

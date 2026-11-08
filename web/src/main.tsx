import React from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import './index.css';
import { AppProvider } from './lib/app';
import Shell from './components/Shell';
import Overview from './pages/Overview';
import Client from './pages/Client';
import Alerts from './pages/Alerts';
import Report from './pages/Report';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <AppProvider>
        <Routes>
          <Route path="/report/:clientId/:month" element={<Report />} />
          <Route element={<Shell />}>
            <Route index element={<Overview />} />
            <Route path="clients/:clientId" element={<Client />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AppProvider>
    </HashRouter>
  </React.StrictMode>,
);

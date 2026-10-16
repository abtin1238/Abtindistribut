import { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { hasToken } from './lib/api'
import Login from './pages/Login'
import Layout from './components/Layout'
import ResourcePage from './components/ResourcePage'
import Dashboard from './pages/Dashboard'
import Ceo from './pages/Ceo'
import Reports from './pages/Reports'
import Settings from './pages/Settings'
import { OrderNew, PurchaseNew, ProposalNew, JournalNew, TransferNew } from './pages/docs'
import StockCountDetail from './pages/StockCountDetail'
import BankReconcile from './pages/BankReconcile'
import AccountTree from './pages/AccountTree'
import JournalTemplates from './pages/JournalTemplates'
import StockReports from './pages/StockReports'
import { resources } from './pages/resources'
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
if (localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark')
export default function App() {
  const [authed, setAuthed] = useState(hasToken())
  if (!authed) return <Login onDone={() => setAuthed(true)} />
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter basename="/app">
        <Routes>
          <Route element={<Layout onLogout={() => { qc.clear(); setAuthed(false) }} />}>
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="ceo" element={<Ceo />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
            <Route path="orders/new" element={<OrderNew />} />
            <Route path="purchases/new" element={<PurchaseNew />} />
            <Route path="transfers/new" element={<TransferNew />} />
            <Route path="proposals/new" element={<ProposalNew />} />
            <Route path="journal/new" element={<JournalNew />} />
            <Route path="stock-counts/:id" element={<StockCountDetail />} />
            <Route path="bank-reconcile" element={<BankReconcile />} />
            <Route path="accounts-tree" element={<AccountTree />} />
            <Route path="journal-templates" element={<JournalTemplates />} />
            <Route path="stock-reports" element={<StockReports />} />
            {resources.map(r => <Route key={r.path} path={r.path} element={<ResourcePage key={r.path} r={r} />} />)}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

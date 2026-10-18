import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/panel.css'
import './styles/react-panel.css'
import { initTheme } from './lib/theme'
import App from './App'
initTheme()
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)

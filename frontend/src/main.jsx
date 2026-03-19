import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './assets/styles/globals.css'
import App from './App.jsx'

// createRoot finds the <div id="root"> in index.html and hands it to React.
// Everything inside <App /> will be rendered inside that div.
// StrictMode runs extra checks in development to catch bugs early — it has
// no effect in production builds.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

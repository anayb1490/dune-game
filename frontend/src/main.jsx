import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './assets/styles/globals.css'
import App from './App.jsx'

const isBoardTest = window.location.search.includes('board_test')

if (isBoardTest) {
  import('./BoardTest.jsx').then(({ default: BoardTest }) => {
    createRoot(document.getElementById('root')).render(
      <StrictMode>
        <BoardTest />
      </StrictMode>,
    )
  })
} else {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

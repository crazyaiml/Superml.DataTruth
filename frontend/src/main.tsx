import React from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import { API_URL } from './config'
import App from './App'
import './index.css'

// Configure axios default base URL
axios.defaults.baseURL = API_URL

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

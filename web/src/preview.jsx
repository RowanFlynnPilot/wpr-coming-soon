// Design preview: the public widget's exact design, rendered over
// queue.json — every unverified signal, clearly badged as such. Internal
// surface for refining the look with real volume; not a publication path.

import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './app.css'

createRoot(document.getElementById('root')).render(<App src="./queue.json" preview />)

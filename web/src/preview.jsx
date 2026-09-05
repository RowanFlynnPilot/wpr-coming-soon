// Design preview: the public widget's exact design, rendered over
// queue.json — every unverified signal, clearly badged as such. Internal
// surface for refining the look with real volume; not a publication path.

import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './app.css'

const el = document.getElementById('root')
;(el._root ||= createRoot(el)).render(<App src="./queue.json" preview />)

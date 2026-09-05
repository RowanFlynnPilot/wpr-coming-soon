import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./app.css";

// Reuse the root across Vite HMR re-executions of this module.
const el = document.getElementById("root");
(el._root ||= createRoot(el)).render(<App />);

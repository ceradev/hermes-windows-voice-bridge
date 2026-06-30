import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

declare const __UI_BUILD_STAMP__: string;
console.info('[Hermes UI] build stamp:', __UI_BUILD_STAMP__);

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

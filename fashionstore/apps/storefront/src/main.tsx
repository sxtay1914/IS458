import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { loadConfig } from './config';
import './styles/app.css';

const root = createRoot(document.getElementById('root')!);
loadConfig()
  .then((config) =>
    root.render(
      <StrictMode>
        <App config={config} />
      </StrictMode>,
    ),
  )
  .catch((e: Error) => root.render(<p className="error">Could not load configuration: {e.message}</p>));

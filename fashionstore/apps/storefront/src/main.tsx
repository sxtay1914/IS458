import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { loadConfig } from './config';
import '@fontsource-variable/nunito';
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
  .catch((e: Error) => root.render(<p className="alert alert-bad">Could not load configuration: {e.message}</p>));

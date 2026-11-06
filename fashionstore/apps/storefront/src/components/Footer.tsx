import { useEffect, useState } from 'react';
import { useApi } from '../api/ApiContext';

/** Shows which pilot API version (v1/v2 weighted target groups) served this page via GET /api/version. */
export function Footer() {
  const api = useApi();
  const [version, setVersion] = useState<string | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    api.version?.()
      .then((v) => live && setVersion(v.version))
      .catch(() => live && setVersion(null));
    return () => {
      live = false;
    };
  }, [api]);

  return (
    <footer className="footer">
      <span>FashionStore · Singapore demo · payments are simulated</span>
      <span className="api-pill" data-testid="api-version" title="store-api version that answered GET /api/version">
        <span className={`dot ${version ? 'dot-ok' : version === null ? 'dot-off' : 'dot-wait'}`} aria-hidden="true" />
        {version ? `API ${version}` : version === null ? 'API unreachable' : 'API …'}
      </span>
    </footer>
  );
}

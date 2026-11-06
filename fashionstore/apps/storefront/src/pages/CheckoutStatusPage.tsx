import { useParams } from 'react-router-dom';
import { useApi } from '../api/ApiContext';
import { CheckoutStatus } from '../components/CheckoutStatus';
import { useCheckoutPolling } from '../hooks/useCheckoutPolling';

export function CheckoutStatusPage() {
  const { checkoutId } = useParams();
  const api = useApi();
  const { status, error, timedOut } = useCheckoutPolling(checkoutId, api.checkoutStatus);
  return (
    <section className="narrow">
      <CheckoutStatus status={status} timedOut={timedOut} />
      {error && <p className="muted center small">Still trying… ({error})</p>}
    </section>
  );
}

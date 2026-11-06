const STEPS = ['Bag', 'Review', 'Done'] as const;

/**
 * Three-step progress track for the buying flow.
 * current: 0 = bag, 1 = review, 2 = placing (waiting for the outcome), 3 = finished.
 * failed marks the last step as unsuccessful (rejected checkout).
 */
export function CheckoutSteps({ current, failed = false }: { current: 0 | 1 | 2 | 3; failed?: boolean }) {
  const pct = (Math.min(current, STEPS.length - 1) / (STEPS.length - 1)) * 100;
  return (
    <ol className={`steps${failed ? ' steps-failed' : ''}`} aria-label="Checkout progress">
      <li className="steps-track" aria-hidden="true">
        <span className="steps-fill" style={{ width: `${pct}%` }} />
      </li>
      {STEPS.map((label, i) => {
        const state = failed && i === 2 ? 'failed' : i < current ? 'done' : i === current ? 'active' : 'todo';
        return (
          <li key={label} className={`step step-${state}`} aria-current={i === current ? 'step' : undefined}>
            <span className="step-dot" aria-hidden="true">
              {state === 'done' ? '✓' : state === 'failed' ? '✕' : i + 1}
            </span>
            <span className="step-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

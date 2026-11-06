/** Small inline icons (stroke = currentColor). Decorative: always aria-hidden. */
const PATHS = {
  bag: 'M6 8h12l-1 12H7L6 8Zm3 0V6a3 3 0 0 1 6 0v2',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  cross: 'M7 7l10 10M17 7L7 17',
  arrow: 'M5 12h13m-5-5 5 5-5 5',
  back: 'M19 12H6m5-5-5 5 5 5',
  box: 'M4 8l8-4 8 4v8l-8 4-8-4V8Zm0 0 8 4 8-4m-8 4v8',
  search: 'M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 4 4',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0',
  bolt: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z',
  hanger: 'M12 7a2 2 0 1 1 2-2c0 1-2 1.5-2 3l9 6.5c.8.6.4 1.5-.5 1.5h-17c-.9 0-1.3-.9-.5-1.5L12 8',
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, className }: { name: IconName; size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={PATHS[name]} />
    </svg>
  );
}

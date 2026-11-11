/** KAVACH mark: kavach means armour. Four tiles (Tessera's family mark) form a shield; the bottom tile is the
 *  verifier, in the "allowed" green: every action passes through it before it reaches the shop. */
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
      <path d="M16 2 4 6.5v9.2C4 23 9.1 28.2 16 30c6.9-1.8 12-7 12-14.3V6.5L16 2Z" stroke="currentColor" strokeOpacity=".28" strokeWidth="1.4" />
      <rect x="8.5" y="8" width="6.5" height="6.5" rx="1.6" fill="currentColor" />
      <rect x="17" y="8" width="6.5" height="6.5" rx="1.6" fill="currentColor" fillOpacity=".45" />
      <rect x="8.5" y="16.5" width="6.5" height="6.5" rx="1.6" fill="currentColor" fillOpacity=".45" />
      <rect x="17" y="16.5" width="6.5" height="6.5" rx="1.6" fill="var(--moss)" />
    </svg>
  );
}
export function Logo({ size = 28 }: { size?: number }) {
  return (<span className="flex items-center gap-2.5 text-bone"><LogoMark size={size} /><span className="text-[16px] font-semibold tracking-[0.14em]">KAVACH</span></span>);
}

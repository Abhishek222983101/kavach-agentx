export default function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-panel3 ${className}`} />;
}

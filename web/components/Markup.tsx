/** Renders the agent's light markup (*bold*, _italic_, as on WhatsApp) safely: text only, never HTML. */
const TOKEN = /(\*[^*\n]{1,200}\*|(?<![\w/])_[^_\n]{1,300}_(?![\w]))/g;

export default function Markup({ text }: { text: string }) {
  const parts = text.split(TOKEN);
  return <>{parts.map((p, i) => {
    if (p.length > 2 && p.startsWith("*") && p.endsWith("*")) return <b key={i} className="font-semibold">{p.slice(1, -1)}</b>;
    if (p.length > 2 && p.startsWith("_") && p.endsWith("_")) return <i key={i} className="text-[0.93em] opacity-75">{p.slice(1, -1)}</i>;
    return <span key={i}>{p}</span>;
  })}</>;
}

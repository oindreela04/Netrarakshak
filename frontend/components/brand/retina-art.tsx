/** Stylised fundus illustration used on the public site. Decorative; not a patient image. */
export function RetinaArt({ className }: { className?: string }) {
  const vessels = [
    "M262 196 C230 170 200 150 150 120 S90 80 60 70",
    "M262 196 C235 180 190 175 140 170 S70 175 40 190",
    "M262 204 C232 225 196 244 152 268 S92 310 66 330",
    "M262 204 C238 214 196 222 150 236 S80 250 46 250",
    "M262 196 C252 160 240 120 228 90 S210 50 200 30",
    "M262 204 C254 240 246 280 236 320 S222 360 214 378",
    "M150 120 C140 140 132 152 118 160",
    "M152 268 C140 252 124 246 104 246",
    "M140 170 C128 160 112 150 96 148",
    "M228 90 C210 92 196 100 180 112",
    "M236 320 C214 314 196 304 182 290",
  ];
  return (
    <svg viewBox="0 0 400 400" className={className} role="img" aria-label="Illustration of a retinal fundus being analysed">
      <defs>
        <radialGradient id="fund" cx="48%" cy="50%" r="55%">
          <stop offset="0%" stopColor="#E0884C" />
          <stop offset="55%" stopColor="#C2562E" />
          <stop offset="100%" stopColor="#6E2414" />
        </radialGradient>
        <radialGradient id="disc" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FFF1C9" />
          <stop offset="70%" stopColor="#F2C27A" />
          <stop offset="100%" stopColor="#E0884C" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="mac" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#5E1D10" stopOpacity=".7" />
          <stop offset="100%" stopColor="#5E1D10" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="sweep" x1="0" x2="1">
          <stop offset="0%" stopColor="#7FD1CB" stopOpacity="0" />
          <stop offset="100%" stopColor="#7FD1CB" stopOpacity=".45" />
        </linearGradient>
        <clipPath id="eye"><circle cx="200" cy="200" r="176" /></clipPath>
      </defs>
      <circle cx="200" cy="200" r="198" fill="#071528" />
      <g clipPath="url(#eye)">
        <circle cx="200" cy="200" r="176" fill="url(#fund)" />
        <circle cx="168" cy="204" r="46" fill="url(#mac)" />
        <circle cx="262" cy="200" r="40" fill="url(#disc)" />
        <g fill="none" stroke="#7A1E10" strokeLinecap="round" opacity=".85">
          {vessels.map((d, i) => <path key={i} d={d} strokeWidth={i < 6 ? 4.2 - i * 0.35 : 1.8} />)}
        </g>
        <path className="retina-sweep" d="M200 200 L200 24 A176 176 0 0 1 340 98 Z" fill="url(#sweep)" />
      </g>
      <circle cx="200" cy="200" r="176" fill="none" stroke="#3E8E8A" strokeWidth="1.5" />
      <circle cx="200" cy="200" r="190" fill="none" stroke="#3E8E8A" strokeOpacity=".35" strokeDasharray="2 6" />
    </svg>
  );
}

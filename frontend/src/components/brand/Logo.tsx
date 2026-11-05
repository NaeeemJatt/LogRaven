// LogRaven — Unified Brand Identity & Logo Component

export interface LogoProps {
  /**
   * 'icon': Just the sovereign cybernetic raven shield icon mark
   * 'full': Icon mark + LogRaven wordmark + optional subtitle / pulse dot
   * 'wordmark': Just the typography
   */
  variant?: 'icon' | 'full' | 'wordmark'
  /** Pixel size of the icon (defaults to 32px) */
  size?: number
  className?: string
  /** Subtitle line beneath LogRaven, e.g. 'Cloud Security SOC' */
  subtitle?: string
  /** Whether to show the live pulsing status dot */
  showSignal?: boolean
}

/**
 * LogRaven Cybernetic Shield & Raven Vector Icon Mark
 */
export function LogoIcon({
  size = 32,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 128 128"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`flex-shrink-0 select-none ${className}`}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="lgr_shieldBg" x1="64" y1="8" x2="64" y2="120" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#151A26" />
          <stop offset="100%" stopColor="#080B12" />
        </linearGradient>
        <linearGradient id="lgr_shieldBorder" x1="16" y1="8" x2="112" y2="120" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.85" />
          <stop offset="50%" stopColor="#3B82F6" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#F59E0B" stopOpacity="0.9" />
        </linearGradient>
        <linearGradient id="lgr_ravenBeak" x1="60" y1="50" x2="108" y2="78" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FEF08A" />
          <stop offset="40%" stopColor="#F59E0B" />
          <stop offset="100%" stopColor="#D97706" />
        </linearGradient>
        <linearGradient id="lgr_wingPlates" x1="20" y1="30" x2="90" y2="110" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#2A344A" />
          <stop offset="60%" stopColor="#1A2234" />
          <stop offset="100%" stopColor="#0E1422" />
        </linearGradient>
        <radialGradient id="lgr_eyeGlow" cx="63" cy="52" r="14" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FEF08A" />
          <stop offset="40%" stopColor="#F59E0B" />
          <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Outer Cyber Shield Contour */}
      <path
        d="M 64,10 L 106,26 L 106,68 Q 106,98 64,118 Q 22,98 22,68 L 22,26 Z"
        fill="url(#lgr_shieldBg)"
        stroke="url(#lgr_shieldBorder)"
        strokeWidth="3.5"
        strokeLinejoin="round"
      />

      {/* Inner Telemetry Radar Rim */}
      <path
        d="M 64,18 L 98,31 L 98,66 Q 98,90 64,108 Q 30,90 30,66 L 30,31 Z"
        fill="none"
        stroke="#384766"
        strokeWidth="1.2"
        strokeDasharray="3 3"
        opacity="0.6"
      />

      {/* Left Wing Armor Facets */}
      <path d="M 33,36 L 54,44 L 46,60 L 32,54 Z" fill="url(#lgr_wingPlates)" stroke="#384766" strokeWidth="1" />
      <path d="M 32,58 L 52,66 L 44,82 L 34,74 Z" fill="url(#lgr_wingPlates)" stroke="#384766" strokeWidth="1" />
      <path d="M 36,80 L 52,86 L 64,104 Q 48,94 36,80 Z" fill="url(#lgr_wingPlates)" stroke="#384766" strokeWidth="1" />

      {/* Raven Head Silhouette & Crown */}
      <path
        d="M 46,30 L 64,20 L 76,28 L 84,38 L 74,44 L 88,48 L 72,56 L 60,48 L 52,38 Z"
        fill="#1E273A"
        stroke="#475569"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />

      {/* Raven Beak (Golden Predator Spear) */}
      <path
        d="M 66,48 L 104,66 L 70,78 L 62,64 Z"
        fill="url(#lgr_ravenBeak)"
        stroke="#FDE047"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
      <path d="M 70,78 L 82,72 L 64,88 L 54,76 L 62,64 Z" fill="#B45309" stroke="#D97706" strokeWidth="1" />

      {/* Cybernetic Eye Sensor */}
      <circle cx="63" cy="52" r="9" fill="url(#lgr_eyeGlow)" />
      <circle cx="63" cy="52" r="3.5" fill="#FEF08A" />
      <circle cx="64" cy="51" r="1.2" fill="#FFFFFF" />

      {/* Tactical Spine Line */}
      <path d="M 64,88 L 64,106" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round" opacity="0.9" />
      <circle cx="64" cy="94" r="1.8" fill="#FEF08A" />
    </svg>
  )
}

/**
 * Complete LogRaven Logo Component with Icon and Typography
 */
export default function Logo({
  variant = 'full',
  size = 32,
  className = '',
  subtitle,
  showSignal = true,
}: LogoProps) {
  if (variant === 'icon') {
    return <LogoIcon size={size} className={className} />
  }

  if (variant === 'wordmark') {
    return (
      <span className={`font-display font-bold tracking-tight text-text-primary ${className}`}>
        Log<span className="text-amber-400">Raven</span>
      </span>
    )
  }

  return (
    <div className={`flex items-center gap-2.5 min-w-0 select-none ${className}`}>
      <div className="relative flex-shrink-0">
        <LogoIcon size={size} />
        {/* Subtle ambient blur behind the shield */}
        <div
          className="absolute inset-0 rounded-lg bg-amber-400/10 blur-sm -z-10"
          style={{ transform: 'scale(0.9)' }}
        />
      </div>

      <div className="flex flex-col leading-none min-w-0">
        <div className="flex items-center gap-1.5">
          <span
            className="font-display font-bold text-text-primary tracking-tight"
            style={{ fontSize: Math.max(14, size * 0.48) }}
          >
            Log<span className="text-amber-400">Raven</span>
          </span>
          {showSignal && (
            <span
              className="rounded-full bg-emerald-400 motion-safe:animate-pulse motion-reduce:animate-none flex-shrink-0"
              style={{ width: 6, height: 6 }}
              title="Platform Live"
            />
          )}
        </div>

        {subtitle && (
          <span className="text-[10px] text-text-muted font-sans mt-0.5 truncate tracking-wide">
            {subtitle}
          </span>
        )}
      </div>
    </div>
  )
}

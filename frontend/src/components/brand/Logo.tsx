// LogRaven — Unified Brand Identity & Logo Component

export interface LogoProps {
  /**
   * 'icon': Just the sovereign cybernetic raven & telemetry logo icon
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
 * LogRaven Cybernetic Raven & Telemetry Icon Mark
 */
export function LogoIcon({
  size = 32,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <img
      src="/logo-icon.png"
      alt="LogRaven"
      width={size}
      height={size}
      className={`rounded-lg object-contain flex-shrink-0 select-none ${className}`}
      style={{ width: size, height: size }}
      loading="eager"
      decoding="async"
    />
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

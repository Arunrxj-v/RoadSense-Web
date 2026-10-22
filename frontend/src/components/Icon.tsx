interface IconProps {
  name: string
  size?: 12 | 14 | 15 | 16 | 18 | 20 | 22
  className?: string
  filled?: boolean
}

export function Icon({ name, size = 20, className = '', filled = false }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined icon-${size} ${className}`.trim()}
      style={filled ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" } : undefined}
      aria-hidden="true"
    >
      {name}
    </span>
  )
}

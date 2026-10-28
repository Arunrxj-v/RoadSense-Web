export type Theme = 'light' | 'dark'

export const THEME_STORAGE_KEY = 'roadsense-theme'

export const THEME_COLORS: Record<Theme, string> = {
  light: '#faf9f5',
  dark: '#111318',
}

export function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark'
}

export function readStoredTheme(): Theme | null {
  if (typeof window === 'undefined') return null
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY)
    return isTheme(value) ? value : null
  } catch {
    return null
  }
}

export function readDocumentTheme(): Theme | null {
  if (typeof document === 'undefined') return null
  const value = document.documentElement.dataset.theme
  return isTheme(value) ? value : null
}

export function initialTheme(): Theme {
  return readDocumentTheme() ?? readStoredTheme() ?? 'light'
}

export function applyTheme(theme: Theme): void {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  root.dataset.theme = theme
  root.style.colorScheme = theme

  const themeColor = document.querySelector('meta[name="theme-color"]')
  themeColor?.setAttribute('content', THEME_COLORS[theme])
}

export function persistTheme(theme: Theme): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme)
  } catch {
    return
  }
}

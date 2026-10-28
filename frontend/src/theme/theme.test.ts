// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import {
  THEME_COLORS,
  THEME_STORAGE_KEY,
  applyTheme,
  initialTheme,
  isTheme,
  persistTheme,
  readDocumentTheme,
  readStoredTheme,
} from './theme'

function createStorage(): Storage {
  const data = new Map<string, string>()
  return {
    get length() {
      return data.size
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (index) => Array.from(data.keys())[index] ?? null,
    removeItem: (key) => {
      data.delete(key)
    },
    setItem: (key, value) => {
      data.set(key, value)
    },
  }
}

describe('theme persistence', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: createStorage(),
    })
    document.documentElement.removeAttribute('data-theme')
    document.head.innerHTML = '<meta name="theme-color" content="#faf9f5" />'
  })

  afterEach(() => {
    window.localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.colorScheme = ''
  })

  it('validates supported themes', () => {
    expect(isTheme('light')).toBe(true)
    expect(isTheme('dark')).toBe(true)
    expect(isTheme('system')).toBe(false)
    expect(isTheme(null)).toBe(false)
  })

  it('persists and reads the selected theme', () => {
    expect(readStoredTheme()).toBeNull()
    persistTheme('dark')
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('dark')
    expect(readStoredTheme()).toBe('dark')
  })

  it('applies the theme to the document and theme-color metadata', () => {
    applyTheme('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(document.documentElement.style.colorScheme).toBe('dark')
    expect(readDocumentTheme()).toBe('dark')
    expect(
      document.querySelector('meta[name="theme-color"]')?.getAttribute('content'),
    ).toBe(THEME_COLORS.dark)
  })

  it('prefers the document theme over stored preference during hydration', () => {
    persistTheme('light')
    applyTheme('dark')
    expect(initialTheme()).toBe('dark')
  })

  it('defaults to light when nothing is stored', () => {
    expect(initialTheme()).toBe('light')
  })
})

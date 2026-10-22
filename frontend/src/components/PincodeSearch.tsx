import { useEffect, useRef, useState, type FormEvent } from 'react'
import { apiErrorMessage, geocodePincode } from '../lib/api'
import type { GeocodeResult } from '../lib/types'
import { Icon } from './Icon'

interface PincodeSearchProps {
  onResolved: (result: GeocodeResult) => void
  onLocate: (latitude: number, longitude: number) => void
}

type SearchState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'success'; message: string }
  | { kind: 'error'; message: string }

export function PincodeSearch({ onResolved, onLocate }: PincodeSearchProps) {
  const [value, setValue] = useState('')
  const [state, setState] = useState<SearchState>({ kind: 'idle' })
  const [locating, setLocating] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)
  const successTimer = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
      if (successTimer.current) window.clearTimeout(successTimer.current)
    }
  }, [])

  const clearSuccessLater = () => {
    if (successTimer.current) window.clearTimeout(successTimer.current)
    successTimer.current = window.setTimeout(() => {
      setState((current) => (current.kind === 'success' ? { kind: 'idle' } : current))
    }, 4500)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const pincode = value.replace(/\s/g, '')
    if (!/^[1-9][0-9]{5}$/.test(pincode)) {
      setState({
        kind: 'error',
        message: 'Enter a valid 6-digit Indian PIN code, for example 691001.',
      })
      return
    }

    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setState({ kind: 'loading' })

    try {
      const result = await geocodePincode(pincode, controller.signal)
      if (controller.signal.aborted) return
      setValue(pincode)
      onResolved(result)
      setState({
        kind: 'success',
        message: `Showing PIN ${pincode}${result.display_name ? ` · ${shortPlace(result.display_name)}` : ''}`,
      })
      clearSuccessLater()
    } catch (error) {
      if (controller.signal.aborted) return
      setState({ kind: 'error', message: apiErrorMessage(error) })
    }
  }

  const locate = () => {
    if (!('geolocation' in navigator)) {
      setState({ kind: 'error', message: 'Location access is not available in this browser.' })
      return
    }
    setLocating(true)
    setState({ kind: 'loading' })
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false)
        onLocate(position.coords.latitude, position.coords.longitude)
        setState({ kind: 'success', message: 'Centred on your current location.' })
        clearSuccessLater()
      },
      (error) => {
        setLocating(false)
        const message =
          error.code === error.PERMISSION_DENIED
            ? 'Location permission was denied. You can search by PIN code instead.'
            : 'Your location could not be determined. Try searching by PIN code.'
        setState({ kind: 'error', message })
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    )
  }

  const isLoading = state.kind === 'loading'

  return (
    <form className={`search-bar${state.kind === 'error' ? ' search-bar--error' : ''}`} onSubmit={submit} role="search">
      <Icon name="search" size={20} className="search-bar__icon" />
      <label className="sr-only" htmlFor="pincode-search">
        Search by Indian PIN code
      </label>
      <input
        id="pincode-search"
        type="text"
        inputMode="numeric"
        autoComplete="postal-code"
        maxLength={6}
        placeholder="Search a pincode (e.g. 691001)"
        value={value}
        onChange={(event) => {
          setValue(event.target.value.replace(/[^0-9]/g, ''))
          if (state.kind === 'error') setState({ kind: 'idle' })
        }}
        aria-describedby={state.kind !== 'idle' ? 'pincode-search-status' : undefined}
        aria-invalid={state.kind === 'error'}
        disabled={isLoading}
      />
      {isLoading ? <span className="spinner" aria-hidden="true" /> : null}
      <button
        type="button"
        className="search-bar__button"
        title="Locate my position"
        aria-label="Centre the map on my current location"
        onClick={locate}
        disabled={isLoading || locating}
      >
        <Icon name="my_location" size={18} />
      </button>
      <button type="submit" className="sr-only">
        Search PIN code
      </button>

      {state.kind !== 'idle' ? (
        <div
          className={`search-bar__status${
            state.kind === 'error'
              ? ' search-bar__status--error'
              : state.kind === 'success'
                ? ' search-bar__status--success'
                : ''
          }`}
          id="pincode-search-status"
          role={state.kind === 'error' ? 'alert' : 'status'}
          aria-live="polite"
        >
          <Icon
            name={state.kind === 'error' ? 'error' : state.kind === 'success' ? 'check_circle' : 'location_searching'}
            size={16}
          />
          <span>{state.kind === 'loading' ? 'Finding location…' : state.message}</span>
        </div>
      ) : null}
    </form>
  )
}

function shortPlace(displayName: string): string {
  const parts = displayName
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
  return parts.slice(0, 2).join(', ')
}

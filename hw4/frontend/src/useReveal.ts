import { useEffect } from 'react'

/** Fade sections up as they scroll into view.
 *
 * Three things keep this from ever hiding content for real:
 *
 *  - the hidden state only applies once JS has added `js-reveal` to <html>, so
 *    without JavaScript — or if this hook never runs — everything is visible;
 *  - anything already within the viewport is shown on the spot rather than
 *    waiting for a scroll that may never come;
 *  - a timeout reveals whatever is left, so a failed observer can never leave
 *    a blank page.
 */
const FAILSAFE_MS = 1200

export function useReveal(deps: unknown[] = []) {
  useEffect(() => {
    const root = document.documentElement
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('.reveal:not(.shown)'))
    if (nodes.length === 0) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced || !('IntersectionObserver' in window)) {
      nodes.forEach((n) => n.classList.add('shown'))
      return
    }

    root.classList.add('js-reveal')

    const show = (n: Element) => n.classList.add('shown')
    const inView = (n: HTMLElement) => {
      const r = n.getBoundingClientRect()
      return r.top < window.innerHeight && r.bottom > 0
    }

    const pending = nodes.filter((n) => {
      if (inView(n)) {
        show(n)
        return false
      }
      return true
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            show(entry.target)
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '0px 0px -6% 0px', threshold: 0.02 },
    )
    pending.forEach((n) => observer.observe(n))

    const failsafe = window.setTimeout(() => {
      document.querySelectorAll('.reveal:not(.shown)').forEach((n) => {
        if (inView(n as HTMLElement)) show(n)
      })
    }, FAILSAFE_MS)

    return () => {
      observer.disconnect()
      window.clearTimeout(failsafe)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/** Placeholder cards while the catalogue loads.
 *
 * The grid keeps its shape instead of collapsing to a line of text, so nothing
 * jumps when the real products arrive.
 */
export default function SkeletonGrid({ count = 8 }: { count?: number }) {
  return (
    <div className="grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="sk sk-thumb" />
          <div className="sk-body">
            <div className="sk sk-line short" />
            <div className="sk sk-line" />
            <div className="sk sk-line mid" />
          </div>
        </div>
      ))}
    </div>
  )
}

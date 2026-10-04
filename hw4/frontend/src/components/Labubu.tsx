/** A Campus Customs Labubu, drawn in SVG rather than shipped as an image.
 *
 * The recognisable bits are the tall ears with the notch halfway up, the wide
 * flat head, the big round eyes and the pointed grin. Everything is sized to
 * still read at 22px in the navigation bar, so the ears are exaggerated and
 * the teeth are triangles rather than squares.
 *
 * Decorative only: hidden from screen readers, because it sits beside a label
 * that already says what the control does.
 */
export default function Labubu({ size = 26 }: { size?: number }) {
  return (
    <span className="labubu" style={{ width: size, height: size }} aria-hidden="true">
      <svg viewBox="0 0 44 44" width={size} height={size} fill="none">
        <g className="labubu-ears">
          {/* left ear: tall, with the notch on the inner edge */}
          <path
            className="labubu-fur"
            d="M15.2 24.6 8.9 3.4c-.5-1.6 1.4-2.7 2.4-1.4l2.9 3.7.3-4.2c.1-1.6 2.2-1.8 2.7-.3l4.6 13.6Z"
          />
          <path
            className="labubu-fur"
            d="M28.8 24.6 35.1 3.4c.5-1.6-1.4-2.7-2.4-1.4l-2.9 3.7-.3-4.2c-.1-1.6-2.2-1.8-2.7-.3l-4.6 13.6Z"
          />
        </g>

        {/* head — wider than tall, the way the toy reads */}
        <path
          className="labubu-fur"
          d="M22 17c9.1 0 15.6 5 15.6 12.6S31.1 42 22 42 6.4 37.2 6.4 29.6 12.9 17 22 17Z"
        />

        {/* pale muzzle */}
        <ellipse className="labubu-face" cx="22" cy="33" rx="10.6" ry="8" />

        {/* eyes */}
        <circle className="labubu-eye" cx="14.8" cy="26" r="3.3" />
        <circle className="labubu-eye" cx="29.2" cy="26" r="3.3" />
        <circle className="labubu-glint" cx="16" cy="24.8" r="1.1" />
        <circle className="labubu-glint" cx="30.4" cy="24.8" r="1.1" />

        {/* nose */}
        <path className="labubu-eye" d="M22 29.3l2.1 2h-4.2l2.1-2Z" />

        {/* the grin: dark mouth, then a row of pointed teeth */}
        <path className="labubu-mouth" d="M13.4 33h17.2c-1.1 4.4-4.9 6.6-8.6 6.6s-7.5-2.2-8.6-6.6Z" />
        <g className="labubu-teeth">
          <path d="M14.1 33h3.2l-1.6 3Z" />
          <path d="M17.7 33h3.2l-1.6 3.5Z" />
          <path d="M21.3 33h3.2l-1.6 3.5Z" />
          <path d="M24.9 33h3.2l-1.6 3.5Z" />
          <path d="M28.5 33h2l-1 2.7Z" />
        </g>
      </svg>
    </span>
  )
}

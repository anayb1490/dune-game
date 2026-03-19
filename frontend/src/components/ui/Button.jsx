/**
 * Reusable Button component.
 * Props:
 *   onClick   - handler function
 *   disabled  - greys out and prevents click
 *   children  - button label text or JSX
 *   variant   - 'primary' (amber) | 'secondary' (dark outline)
 *   className - extra Tailwind classes to merge in
 */
export default function Button({ onClick, disabled, children, variant = 'primary', className = '' }) {
  const base = 'px-4 py-2 rounded font-semibold text-sm tracking-wide transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed'

  const variants = {
    primary: 'bg-sand text-black hover:bg-sand-light active:scale-95',
    secondary: 'bg-transparent border border-[#3a3020] text-sand hover:border-sand hover:text-sand-light',
    danger: 'bg-red-800 text-white hover:bg-red-700 active:scale-95',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant] ?? variants.primary} ${className}`}
    >
      {children}
    </button>
  )
}

export default function SocratesLogo({
  size = 48,
  className = '',
}) {
  return (
    <div
      className={`overflow-hidden flex items-center justify-center ${className}`}
      style={{
        width: size,
        height: size
      }}
    >
      <img
        src="/socrates-nobg.png"
        alt="Socrates"
        className="w-full h-full object-contain"
        style={{
          filter: 'drop-shadow(0 2px 4px rgba(107, 124, 94, 0.3))'
        }}
      />
    </div>
  )
}

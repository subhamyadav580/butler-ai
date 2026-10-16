/** Butler's mark (a bow tie), served from public/favicon.svg so the tab icon and the UI match. */
export function Logo({ size = 28 }: { size?: number }) {
  return <img className="logo" src="/favicon.svg" width={size} height={size} alt="" aria-hidden />
}

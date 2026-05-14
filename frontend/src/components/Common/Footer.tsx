export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t py-6 px-6">
      <div className="flex flex-col items-center gap-2">
        <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
          XEPHORA
        </p>
        <p className="text-[10px] text-muted-foreground">
          &copy; {currentYear} Xephora. All rights reserved.
        </p>
      </div>
    </footer>
  )
}

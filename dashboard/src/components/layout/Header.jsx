export default function Header() {
  return (
    <header className="sticky top-0 bg-white border-b border-gray-200 z-10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <span className="font-semibold text-brand-blue">STI Notification — Scenario Dashboard</span>
        <nav className="flex gap-4 text-sm text-brand-gray">
          <a href="#overview" className="hover:text-brand-teal">Overview</a>
          <a href="#explorer" className="hover:text-brand-teal">Explorer</a>
          <a href="#findings" className="hover:text-brand-teal">Findings</a>
          <a href="#methods" className="hover:text-brand-teal">Methods</a>
        </nav>
      </div>
    </header>
  );
}

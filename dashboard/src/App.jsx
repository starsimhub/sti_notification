import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import Overview from './components/sections/Overview.jsx';
import ScenarioExplorer from './components/sections/ScenarioExplorer.jsx';
import KeyFindings from './components/sections/KeyFindings.jsx';
import Methods from './components/sections/Methods.jsx';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <Header />
      <main className="flex-1">
        <Overview />
        <ScenarioExplorer />
        <KeyFindings />
        <Methods />
      </main>
      <Footer />
    </div>
  );
}

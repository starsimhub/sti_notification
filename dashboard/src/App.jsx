import Header from './components/layout/Header.jsx';
import Footer from './components/layout/Footer.jsx';
import TheProblem from './components/sections/TheProblem.jsx';
import ResultsHowPocHelps from './components/sections/ResultsHowPocHelps.jsx';
import Hypothesis from './components/sections/Hypothesis.jsx';
import ResultsCombinedStrategies from './components/sections/ResultsCombinedStrategies.jsx';
import ScenarioExplorer from './components/sections/ScenarioExplorer.jsx';
import Methods from './components/sections/Methods.jsx';

export default function App() {
  return (
    <div className="min-h-screen flex flex-col font-sans">
      <Header />
      <main className="flex-1">
        <TheProblem />
        <ResultsHowPocHelps />
        <Hypothesis />
        <ResultsCombinedStrategies />
        <ScenarioExplorer />
        <Methods />
      </main>
      <Footer />
    </div>
  );
}

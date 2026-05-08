/**
 * Main App component
 */

import { useState } from 'react';
import { InputPanel } from './components/InputPanel';
import { DiffViewer } from './components/DiffViewer';
import { SummaryBar } from './components/SummaryBar';
import { CompareResponse } from './types/api';
import './styles/App.css';

function App() {
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);

  return (
    <div className="app">
      <header>
        <h1>Semantic Diff</h1>
        <p>Git diff for prose - compare documents by meaning, not just words</p>
      </header>

      <main>
        {!compareResult ? (
          <InputPanel onCompareComplete={setCompareResult} />
        ) : (
          <>
            <button className="reset-btn" onClick={() => setCompareResult(null)}>
              ← New Comparison
            </button>
            <DiffViewer pairs={compareResult.pairs} summary={compareResult.summary} />
            <SummaryBar summary={compareResult.summary} />
          </>
        )}
      </main>
    </div>
  );
}

export default App;

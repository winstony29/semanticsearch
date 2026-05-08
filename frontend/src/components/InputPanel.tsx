/**
 * InputPanel component - FE Engineer 2's domain
 *
 * Two text areas for pasting v1 and v2, with a "Compare" button.
 * Handles loading state and API call.
 */

import { useState } from 'react';
import { compareDocuments } from '../api/client';
import { CompareResponse } from '../types/api';

interface InputPanelProps {
  onCompareComplete: (result: CompareResponse) => void;
}

export function InputPanel({ onCompareComplete }: InputPanelProps) {
  const [v1Text, setV1Text] = useState('');
  const [v2Text, setV2Text] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompare = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await compareDocuments({
        v1_text: v1Text,
        v2_text: v2Text
      });
      onCompareComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare documents');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="input-panel">
      <h2>Compare Documents</h2>

      <div className="text-areas">
        <div className="text-area-container">
          <label>Version 1 (Original)</label>
          <textarea
            value={v1Text}
            onChange={(e) => setV1Text(e.target.value)}
            placeholder="Paste original text here..."
            disabled={isLoading}
          />
        </div>

        <div className="text-area-container">
          <label>Version 2 (Revised)</label>
          <textarea
            value={v2Text}
            onChange={(e) => setV2Text(e.target.value)}
            placeholder="Paste revised text here..."
            disabled={isLoading}
          />
        </div>
      </div>

      <button onClick={handleCompare} disabled={isLoading || !v1Text || !v2Text}>
        {isLoading ? 'Comparing...' : 'Compare'}
      </button>

      {error && <div className="error">{error}</div>}
    </div>
  );
}

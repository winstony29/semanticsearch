/**
 * DiffViewer component - FE Engineer 1's domain
 *
 * Side-by-side view of v1 (left) and v2 (right).
 * Color-codes sentences by severity.
 * Shows similarity scores and handles accept/reject.
 */

import { useState } from 'react';
import { SentencePair, DocumentSummary, SEVERITY_BACKGROUNDS } from '../types/api';

interface DiffViewerProps {
  pairs: SentencePair[];
  summary: DocumentSummary;
}

export function DiffViewer({ pairs, summary }: DiffViewerProps) {
  const [hoveredPairId, setHoveredPairId] = useState<string | null>(null);
  const [acceptedPairs, setAcceptedPairs] = useState<Set<string>>(new Set());
  const [rejectedPairs, setRejectedPairs] = useState<Set<string>>(new Set());

  const handleAccept = (pairId: string) => {
    setAcceptedPairs(prev => new Set(prev).add(pairId));
    setRejectedPairs(prev => {
      const next = new Set(prev);
      next.delete(pairId);
      return next;
    });
  };

  const handleReject = (pairId: string) => {
    setRejectedPairs(prev => new Set(prev).add(pairId));
    setAcceptedPairs(prev => {
      const next = new Set(prev);
      next.delete(pairId);
      return next;
    });
  };

  return (
    <div className="diff-viewer">
      <h2>Semantic Diff Results</h2>

      <div className="diff-container">
        <div className="v1-column">
          <h3>Version 1 (Original)</h3>
          {pairs.map((pair) => (
            <div
              key={pair.pair_id}
              className={`sentence ${hoveredPairId === pair.pair_id ? 'highlighted' : ''}`}
              onMouseEnter={() => setHoveredPairId(pair.pair_id)}
              onMouseLeave={() => setHoveredPairId(null)}
            >
              {pair.v1_sentence || <span className="deleted">[DELETED]</span>}
            </div>
          ))}
        </div>

        <div className="v2-column">
          <h3>Version 2 (Revised)</h3>
          {pairs.map((pair) => (
            <div
              key={pair.pair_id}
              className={`sentence ${hoveredPairId === pair.pair_id ? 'highlighted' : ''}`}
              style={{ backgroundColor: SEVERITY_BACKGROUNDS[pair.severity] }}
              onMouseEnter={() => setHoveredPairId(pair.pair_id)}
              onMouseLeave={() => setHoveredPairId(null)}
            >
              <div className="sentence-content">
                {pair.v2_sentence || <span className="added">[ADDED]</span>}
                {pair.status === 'matched' && (
                  <span className="score-badge">
                    {Math.round(pair.similarity_score * 100)}%
                  </span>
                )}
              </div>

              {pair.status === 'matched' && (
                <div className="actions">
                  <button
                    onClick={() => handleAccept(pair.pair_id)}
                    className={acceptedPairs.has(pair.pair_id) ? 'active' : ''}
                  >
                    Accept
                  </button>
                  <button
                    onClick={() => handleReject(pair.pair_id)}
                    className={rejectedPairs.has(pair.pair_id) ? 'active' : ''}
                  >
                    Reject
                  </button>
                </div>
              )}

              {pair.explanation && (
                <div className="explanation">{pair.explanation}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

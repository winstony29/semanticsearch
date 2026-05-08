/**
 * SummaryBar component - FE Engineer 2's domain
 *
 * Bottom bar showing overall stats and bulk actions.
 */

import { DocumentSummary } from '../types/api';

interface SummaryBarProps {
  summary: DocumentSummary;
  onAcceptAll?: () => void;
  onRejectAll?: () => void;
}

export function SummaryBar({ summary, onAcceptAll, onRejectAll }: SummaryBarProps) {
  const accuracyPercent = Math.round(summary.overall_score * 100);
  const barColor = accuracyPercent >= 85 ? '#22c55e' : accuracyPercent >= 60 ? '#eab308' : '#ef4444';

  return (
    <div className="summary-bar">
      <div className="summary-stats">
        <div className="overall-score">
          <label>Overall Semantic Accuracy</label>
          <div className="progress-bar-container">
            <div
              className="progress-bar"
              style={{ width: `${accuracyPercent}%`, backgroundColor: barColor }}
            />
          </div>
          <span className="percentage">{accuracyPercent}%</span>
        </div>

        <div className="counts">
          <span className="count green">{summary.green_count} green</span>
          <span className="count yellow">{summary.yellow_count} yellow</span>
          <span className="count red">{summary.red_count} red</span>
          <span className="count added">{summary.added_count} added</span>
          <span className="count deleted">{summary.deleted_count} deleted</span>
        </div>
      </div>

      <div className="bulk-actions">
        <button onClick={onAcceptAll}>Accept All</button>
        <button onClick={onRejectAll}>Reject All</button>
      </div>
    </div>
  );
}

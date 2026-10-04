import React, { useState } from 'react';
import { 
  ShieldCheck, AlertTriangle, ShieldAlert, CheckCircle2, 
  ChevronDown, ChevronUp, Layers, HelpCircle 
} from 'lucide-react';
import { GlassPanel } from '../ui/GlassPanel';
import { Badge } from '../ui/Badge';
import './GroundingPanel.css';

export const GroundingPanel = ({ grounding, provider, model }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!grounding) return null;

  const status = grounding.status || 'UNKNOWN';
  const confidence = typeof grounding.confidence === 'number' ? grounding.confidence : 0;
  const confidencePercent = Math.round(confidence * 100);
  const conflicts = grounding.conflicts || [];
  const supportedClaims = grounding.supported_claims || [];
  const unsupportedClaims = grounding.unsupported_claims || [];
  const sourceChunkIds = grounding.source_chunk_ids || [];

  const getStatusBadge = () => {
    switch (status) {
      case 'SUPPORTED':
        return (
          <Badge variant="success" icon={<ShieldCheck size={14} />}>
            Verified Grounded
          </Badge>
        );
      case 'CONFLICTING_EVIDENCE':
        return (
          <Badge variant="danger" icon={<ShieldAlert size={14} />}>
            Conflicting Evidence Detected
          </Badge>
        );
      case 'PARTIALLY_SUPPORTED':
        return (
          <Badge variant="warning" icon={<AlertTriangle size={14} />}>
            Partially Supported
          </Badge>
        );
      case 'INSUFFICIENT_EVIDENCE':
        return (
          <Badge variant="default" icon={<HelpCircle size={14} />}>
            Insufficient Evidence
          </Badge>
        );
      default:
        return <Badge variant="default">{status}</Badge>;
    }
  };

  return (
    <GlassPanel className={`grounding-panel ${status === 'CONFLICTING_EVIDENCE' ? 'has-conflicts' : ''}`}>
      <div className="grounding-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="grounding-header-left">
          <div className="grounding-title-group">
            <h3 className="grounding-title">Evidence Grounding & Verification</h3>
            <span className="grounding-subtitle">Deterministic attribution & factual integrity</span>
          </div>
          <div className="grounding-badges">
            {getStatusBadge()}
            <span className="grounding-confidence-pill">
              <span className="confidence-label">Confidence</span>
              <span className="confidence-value">{confidencePercent}%</span>
            </span>
          </div>
        </div>

        <div className="grounding-header-right">
          <span className="grounding-chunk-stat">
            <Layers size={13} /> {sourceChunkIds.length} source chunk{sourceChunkIds.length === 1 ? '' : 's'}
          </span>
          <button type="button" className="grounding-expand-btn">
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      {status === 'CONFLICTING_EVIDENCE' && (
        <div className="grounding-conflict-alert">
          <AlertTriangle size={16} className="text-danger shrink-0" />
          <div className="conflict-alert-content">
            <div className="conflict-alert-title">Material Incompatibility Discovered</div>
            <p className="conflict-alert-desc">
              Both documents make contradictory claims for identical metrics or policies. The engine has highlighted these values neutrally without favoring either version.
            </p>
          </div>
        </div>
      )}

      {isExpanded && (
        <div className="grounding-body">
          {conflicts.length > 0 && (
            <div className="grounding-section">
              <div className="grounding-section-header text-danger">
                <AlertTriangle size={14} /> Detected Discrepancies ({conflicts.length})
              </div>
              <ul className="grounding-list conflict-list">
                {conflicts.map((conf, i) => (
                  <li key={i} className="grounding-list-item conflict-item">
                    {conf}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {supportedClaims.length > 0 && (
            <div className="grounding-section">
              <div className="grounding-section-header">
                <CheckCircle2 size={14} className="text-success" /> Supported Grounded Claims ({supportedClaims.length})
              </div>
              <ul className="grounding-list">
                {supportedClaims.slice(0, 10).map((claim, i) => (
                  <li key={i} className="grounding-list-item">
                    {claim}
                  </li>
                ))}
                {supportedClaims.length > 10 && (
                  <li className="grounding-more-hint">
                    + {supportedClaims.length - 10} more verified claims
                  </li>
                )}
              </ul>
            </div>
          )}

          {unsupportedClaims.length > 0 && (
            <div className="grounding-section">
              <div className="grounding-section-header text-warning">
                <AlertTriangle size={14} /> Unsupported / Unverified Claims ({unsupportedClaims.length})
              </div>
              <ul className="grounding-list">
                {unsupportedClaims.map((claim, i) => (
                  <li key={i} className="grounding-list-item text-warning">
                    {claim}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="grounding-footer-telemetry">
            <div className="telemetry-item">
              <span className="telemetry-label">Analysis Synthesis:</span>
              <span className="telemetry-value">
                {provider === 'gemini' ? 'Google Gemini 2.5 Flash' : (provider || 'Local Heuristic Fallback')}
              </span>
            </div>
            {model && (
              <div className="telemetry-item">
                <span className="telemetry-label">Model:</span>
                <span className="telemetry-value">{model}</span>
              </div>
            )}
            <div className="telemetry-item">
              <span className="telemetry-label">Verification Engine:</span>
              <span className="telemetry-value">Deterministic Semantic Guard</span>
            </div>
          </div>
        </div>
      )}
    </GlassPanel>
  );
};

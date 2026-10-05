import { TagHelp } from './tag-tooltip.jsx';
import { processStateMeaning } from '../services/process-state.js';

export function ProcessState({ value, className }) {
  return <TagHelp className="process-state-tooltip" description={processStateMeaning(value)}><span className={className}>{value || '상태 미상'}</span></TagHelp>;
}

import { cloneElement, useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link } from 'react-router';
import { tagMeaning } from '../services/tag-presentation.js';

// Portal outside scrolling rows; use the dialog's top layer when a modal is open.
export function TagHelp({ description, children, className = '' }) {
  const id = useId();
  const anchor = useRef(null);
  const closeTimer = useRef(null);
  const [placement, setPlacement] = useState(null);
  function cancelClose() { clearTimeout(closeTimer.current); }
  function close() { cancelClose(); setPlacement(null); }
  function show() {
    cancelClose();
    const rect = anchor.current.getBoundingClientRect();
    const width = Math.min(240, window.innerWidth - 32);
    setPlacement({
      parent: anchor.current.closest('dialog[open]') ?? document.body,
      style: { position: 'fixed', width, left: Math.max(16, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - 16)),
        ...(rect.top > 150 ? { bottom: window.innerHeight - rect.top + 8 } : { top: rect.bottom + 8 }),
        transform: 'none', zIndex: 100 },
    });
  }
  useEffect(() => {
    if (!placement) return;
    function dismiss() { setPlacement(null); }
    window.addEventListener('resize', dismiss);
    window.addEventListener('scroll', dismiss, true);
    return () => { window.removeEventListener('resize', dismiss); window.removeEventListener('scroll', dismiss, true); };
  }, [placement]);
  useEffect(() => () => clearTimeout(closeTimer.current), []);
  if (!description) return children;
  const control = cloneElement(children, {
    'aria-describedby': placement ? id : children.props['aria-describedby'],
    onKeyDown: (event) => { children.props.onKeyDown?.(event); if (event.key === 'Escape') setPlacement(null); },
  });
  return <span ref={anchor} className={`tag-tooltip-anchor ${className}`} onMouseEnter={show}
    onMouseLeave={() => { closeTimer.current = setTimeout(close, 100); }}
    onFocusCapture={show} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) close(); }}>
    {control}
    {placement && createPortal(<span id={id} role="tooltip" className="tag-tooltip tag-tooltip-floating" style={placement.style}
      onMouseEnter={cancelClose} onMouseLeave={close}>{description}</span>, placement.parent)}
  </span>;
}

export function TagTooltip({ tag, to }) {
  return <TagHelp description={tagMeaning(tag)}>
    <Link className="discovery-chip" to={to}>{tag.label}<span aria-hidden="true"> {tag.emoji}</span></Link>
  </TagHelp>;
}

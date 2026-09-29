import { useId, useRef, useState } from 'react';
import { Button } from './button.jsx';
import { discoveryTags, regionOptions, tagGroups, updateDiscoveryQuery } from '../services/discovery-query.js';

export function SelectField({ label, value, options, onChange, disabled = false, allLabel = '전체', name }) {
  const id = useId();
  const unknown = value && !options.some((option) => option.value === value);
  return <div className="filter-field">
    <label htmlFor={id}>{label}</label>
    <select id={id} name={name} value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
      <option value="">{allLabel}</option>
      {unknown && <option value={value}>현재 선택: {value}</option>}
      {options.map((option) => <option key={option.value} value={option.value}>{option.label ?? option.value}</option>)}
    </select>
  </div>;
}

export function QuickTags({ tags, selected = [], onToggle }) {
  return <div className="quick-tags-row" role="group" aria-label="빠른 태그 선택">
    {discoveryTags(tags).slice(0, 7).map((tag) => <button key={tag.key} type="button" className="discovery-chip" aria-pressed={selected.includes(tag.key)} onClick={() => onToggle(tag.key)}>
      {tag.emoji && <span aria-hidden="true">{tag.emoji} </span>}{tag.label}
    </button>)}
  </div>;
}

export function FilterDialog({ filters, tags, state, onApply }) {
  const dialog = useRef(null);
  const trigger = useRef(null);
  const titleId = useId();
  const dialogId = useId();
  const [draft, setDraft] = useState(state);
  const regions = regionOptions(filters, draft.sido);
  const count = ['sido', 'sigungu', 'breed', 'sex', 'neutered', 'size_group', 'age_group', 'process_state'].filter((key) => state[key]).length + state.tag.length;
  function update(changes) { setDraft((value) => updateDiscoveryQuery(value, changes)); }
  function open() { setDraft({ ...state, tag: [...state.tag] }); dialog.current.showModal(); }
  function close() { dialog.current.close(); }
  function keepFocus(event) {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.current.querySelectorAll('button, input, select, [href], [tabindex]')]
      .filter((element) => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && event.target === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && event.target === last) { event.preventDefault(); first?.focus(); }
  }
  function apply(event) { event.preventDefault(); close(); onApply({ ...draft, page: 1 }); }
  return <>
    <Button ref={trigger} variant="secondary" onClick={open} aria-haspopup="dialog" aria-controls={dialogId}>
      <span aria-hidden="true">☷</span> 필터{count > 0 && <span className="filter-count">{count}</span>}
    </Button>
    <dialog ref={dialog} id={dialogId} className="filter-dialog" aria-labelledby={titleId} onKeyDown={keepFocus} onClose={() => trigger.current?.focus()}>
      <div className="filter-dialog-heading"><div><p className="eyebrow">A LITTLE CLOSER</p><h2 id={titleId}>어떤 친구를 만나고 싶나요?</h2></div><Button variant="secondary" onClick={close} aria-label="필터 닫기">✕</Button></div>
      <form onSubmit={apply} className="filter-dialog-form">
        <div className="filter-dialog-body">
          <div className="filter-fields">
            <SelectField label="시도" name="sido" value={draft.sido} options={regions.sido} onChange={(sido) => update({ sido })} />
            <SelectField label="시군구" name="sigungu" value={draft.sigungu} options={regions.sigungu} onChange={(sigungu) => update({ sigungu })} disabled={!draft.sido} allLabel={draft.sido ? '전체' : '시도를 먼저 선택하세요'} />
            <SelectField label="품종" name="breed" value={draft.breed} options={filters.breeds} onChange={(breed) => update({ breed })} />
            <SelectField label="보호 상태" name="process_state" value={draft.process_state} options={filters.process_states} onChange={(process_state) => update({ process_state })} />
            <SelectField label="크기" name="size_group" value={draft.size_group} options={filters.size_groups} onChange={(size_group) => update({ size_group })} />
            <SelectField label="나이" name="age_group" value={draft.age_group} options={filters.age_groups} onChange={(age_group) => update({ age_group })} />
            <SelectField label="성별" name="sex" value={draft.sex} options={filters.sexes} onChange={(sex) => update({ sex })} />
            <SelectField label="중성화" name="neutered" value={draft.neutered} options={filters.neutered} onChange={(neutered) => update({ neutered })} />
          </div>
          <fieldset className="mt-7"><legend className="mb-2 font-semibold">태그</legend><p className="mb-3 text-sm text-muted">원천 정보에 근거한 특징이에요. 성격을 단정하지 않아요.</p>
            <div className="grid gap-4">{tagGroups(discoveryTags(tags)).map((group) => <fieldset key={group.key}>
              <legend className="mb-2 text-sm font-semibold text-muted">{group.label}</legend>
              <div className="flex flex-wrap gap-2">{group.tags.map((tag) => <label key={tag.key} className="tag-checkbox">
              <input type="checkbox" name="tag" value={tag.key} checked={draft.tag.includes(tag.key)} onChange={() => update({ tag: draft.tag.includes(tag.key) ? draft.tag.filter((key) => key !== tag.key) : [...draft.tag, tag.key] })} />
              <span>{tag.emoji && <span aria-hidden="true">{tag.emoji} </span>}{tag.label}</span>
            </label>)}</div></fieldset>)}</div>
          </fieldset>
          {draft.tag.length > 1 && <div className="mt-4"><SelectField label="여러 태그 일치 방식" value={draft.tag_match} options={[{ value: 'any', label: '하나 이상 일치' }, { value: 'all', label: '모두 일치' }]} onChange={(tag_match) => update({ tag_match: tag_match || 'any' })} allLabel="하나 이상 일치" /></div>}
        </div>
        <div className="filter-dialog-footer">
          <Button variant="secondary" onClick={() => setDraft({ ...draft, sido: '', sigungu: '', breed: '', sex: '', neutered: '', size_group: '', age_group: '', process_state: '', tag: [], tag_match: 'any' })}>필터 초기화</Button>
          <Button type="submit">선택한 조건 적용</Button>
        </div>
      </form>
    </dialog>
  </>;
}

export function ActiveFilters({ state, filters, tags, onRemove, onReset }) {
  const regions = regionOptions(filters, state.sido);
  const catalogs = { sido: regions.sido, sigungu: regions.sigungu, breed: filters.breeds, sex: filters.sexes, neutered: filters.neutered, size_group: filters.size_groups, age_group: filters.age_groups, process_state: filters.process_states };
  const labels = { sido: '시도', sigungu: '시군구', breed: '품종', sex: '성별', neutered: '중성화', size_group: '크기', age_group: '나이', process_state: '상태', q: '검색' };
  const active = Object.keys(labels).filter((key) => state[key]).map((key) => ({ key, label: `${labels[key]}: ${catalogs[key]?.find((item) => item.value === state[key])?.label ?? state[key]}`, changes: key === 'sido' ? { sido: '', sigungu: '' } : { [key]: '' } }));
  for (const key of state.tag) active.push({ key: `tag-${key}`, label: tags.find((tag) => tag.key === key)?.label ?? key, changes: { tag: state.tag.filter((tag) => tag !== key) } });
  if (!active.length) return null;
  return <div className="flex flex-wrap items-center gap-2" aria-label="적용된 조건">
    {active.map((item) => <button type="button" key={item.key} className="active-filter" onClick={() => onRemove(item.changes)} aria-label={`${item.label} 조건 해제`}>{item.label}<span aria-hidden="true"> ×</span></button>)}
    <button type="button" className="min-h-11 px-3 text-sm underline" onClick={onReset}>모두 초기화</button>
  </div>;
}

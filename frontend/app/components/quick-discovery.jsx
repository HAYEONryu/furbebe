import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Button } from './button.jsx';
import { TagTooltip } from './tag-tooltip.jsx';
import { SelectField } from './discovery-filters.jsx';
import { discoveryHref, discoveryTags, regionOptions } from '../services/discovery-query.js';

export function QuickDiscovery({ filters, tags }) {
  const navigate = useNavigate();
  const [selection, setSelection] = useState({ sido: '', size_group: '', age_group: '', breed: '' });
  const suggestedTags = discoveryTags(tags);
  const choose = (key) => (value) => setSelection((state) => ({ ...state, [key]: value }));
  return <section className="discovery-section" aria-labelledby="quick-discovery-title">
    <div><p className="eyebrow">START WITH A LITTLE CURIOSITY</p><h2 id="quick-discovery-title" className="section-title">어떤 만남을 찾고 있나요?</h2><p className="mt-2 text-muted">가까운 곳에서, 나와 맞는 친구를 천천히 찾아보세요.</p></div>
    <form className="quick-discovery-form" onSubmit={(event) => { event.preventDefault(); navigate(discoveryHref(selection)); }}>
      <SelectField label="함께할 지역" value={selection.sido} options={regionOptions(filters, '').sido} onChange={choose('sido')} allLabel="어디든 좋아요" />
      <SelectField label="품종" value={selection.breed} options={filters.breeds} onChange={choose('breed')} allLabel="모든 품종" />
      <SelectField label="크기" value={selection.size_group} options={filters.size_groups.filter((item) => item.value !== 'unknown')} onChange={choose('size_group')} allLabel="모든 크기" />
      <SelectField label="나이" value={selection.age_group} options={filters.age_groups.filter((item) => item.value !== 'unknown')} onChange={choose('age_group')} allLabel="모든 나이" />
      <Button type="submit">친구 찾아보기 <span aria-hidden="true">↗</span></Button>
    </form>
    {suggestedTags.length > 0 && <div className="mt-5 flex flex-wrap items-center gap-2"><span className="mr-2 text-sm text-muted">이런 친구는 어때요?</span>{suggestedTags.map((tag) => <TagTooltip key={tag.key} tag={tag} to={discoveryHref({ tag: [tag.key] })} />)}</div>}
  </section>;
}

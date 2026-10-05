import { useId, useRef, useState } from 'react';
import { AnimalImage } from './animal-image.jsx';
import { sourceImages } from '../services/animal-detail.js';

export function ImageGallery({ images, name }) {
  const photos = sourceImages(images);
  const [selected, setSelected] = useState(0);
  const buttons = useRef([]);
  const failed = useRef(new Set());
  const manuallySelected = useRef(false);
  function selectPhoto(index) {
    manuallySelected.current = true;
    setSelected(index);
  }
  function recordFailure(url) {
    failed.current.add(url);
  }
  function selectAvailable(url) {
    recordFailure(url);
    if (manuallySelected.current) return;
    const next = photos.findIndex((photo) => !failed.current.has(photo.url));
    if (next >= 0) setSelected(next);
  }
  const panelId = useId();
  function navigate(event, index) {
    const next = { ArrowRight: (index + 1) % photos.length, ArrowLeft: (index - 1 + photos.length) % photos.length, Home: 0, End: photos.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    selectPhoto(next);
    buttons.current[next]?.focus();
  }
  return <section className="detail-gallery" aria-label="아이의 사진">
    <figure>
      <div id={panelId} className="gallery-image"><AnimalImage src={photos[selected]?.url} alt={`${name}의 보호소 등록 사진 ${selected + 1}`} priority onError={selectAvailable} /></div>
      <figcaption className="gallery-caption"><span>보호소에 등록된 사진</span>{photos.length > 0 && <span role="status" aria-live="polite">{selected + 1} / {photos.length}</span>}</figcaption>
    </figure>
    {photos.length > 1 && <ul className="gallery-thumbnails" aria-label="사진 선택">
      {photos.map((photo, index) => <li key={photo.url}><button type="button" ref={(element) => { buttons.current[index] = element; }} onClick={() => selectPhoto(index)} onKeyDown={(event) => navigate(event, index)} aria-label={`사진 ${index + 1} 보기`} aria-pressed={selected === index} aria-controls={panelId}>
        <AnimalImage src={photo.url} alt="" failureLabel="사진 로딩 실패" onError={recordFailure} />
      </button></li>)}
    </ul>}
  </section>;
}

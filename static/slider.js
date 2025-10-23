// 무한 루프 슬라이더 (끝↔처음도 한 칸만 부드럽게, 중간 슬라이드 노출 없음)
(function () {
  const SLIDE_WIDTH = 440;                  // .slick-slide의 가로폭과 동일해야 함
  const TRANSITION = 'transform 300ms ease';

  const sliders = [
    { trackId: 'trackA', pageId: 'pageA', leftSel: ".btn-slick.left[data-target='A']", rightSel: ".btn-slick.right[data-target='A']" },
    { trackId: 'trackB', pageId: 'pageB', leftSel: ".btn-slick.left[data-target='B']", rightSel: ".btn-slick.right[data-target='B']" },
  ];

  // trackId -> { idx(0~total-1), total, pos(클론 포함 위치), animating }
  const state = {};

  sliders.forEach(s => initSlider(s));

  function initSlider({ trackId, pageId, leftSel, rightSel }) {
    const track = document.getElementById(trackId);
    if (!track) return;

    const originals = Array.from(track.children); // .slick-slide 들
    const total = originals.length;
    if (!total) return;

    // 양끝 클론 삽입: [lastClone, ...originals..., firstClone]
    const firstClone = originals[0].cloneNode(true);
    const lastClone  = originals[total - 1].cloneNode(true);
    track.insertBefore(lastClone, track.firstChild);
    track.appendChild(firstClone);

    // 초기 상태
    state[trackId] = { idx: 0, total, pos: 1, animating: false };

    // 기본 스타일
    track.style.willChange = 'transform';
    track.style.transition = TRANSITION;

    // 첫 실제 슬라이드가 보이도록 이동(클론 뒤)
    applyTransform(track, 1);
    updatePage(trackId, pageId);

    // 전환 종료 시 스냅 처리 + 애니메이션 플래그 해제
    track.addEventListener('transitionend', () => {
      const st = state[trackId];
      if (!st) return;

      // 끝 클론(= firstClone)에서 스냅 → 첫 실제(=pos 1)
      if (st.pos === st.total + 1) {
        track.style.transition = 'none';
        st.pos = 1;
        applyTransform(track, st.pos);
        // 강제 리플로우 후 transition 복구
        track.offsetHeight;
        track.style.transition = TRANSITION;
      }

      // 앞 클론(= lastClone)에서 스냅 → 마지막 실제(=pos total)
      if (st.pos === 0) {
        track.style.transition = 'none';
        st.pos = st.total;
        applyTransform(track, st.pos);
        track.offsetHeight;
        track.style.transition = TRANSITION;
      }

      // 애니메이션 종료
      st.animating = false;
    });

    // 버튼
    const leftBtn  = document.querySelector(leftSel);
    const rightBtn = document.querySelector(rightSel);

    leftBtn  && leftBtn.addEventListener('click', () => move(trackId, -1, pageId));
    rightBtn && rightBtn.addEventListener('click', () => move(trackId, +1, pageId));
  }

  function applyTransform(track, pos) {
    track.style.transform = `translate3d(${-SLIDE_WIDTH * pos}px, 0, 0)`;
  }

  function updatePage(trackId, pageId) {
    const st = state[trackId];
    const page = document.getElementById(pageId);
    if (page && st) page.textContent = `${st.idx + 1}/${st.total}`;
  }

  function move(trackId, delta, pageId) {
    const track = document.getElementById(trackId);
    const st = state[trackId];
    if (!track || !st) return;
    if (st.animating) return;      // 애니메이션 중엔 입력 무시
    st.animating = true;

    const atFirstReal = st.pos === 1;
    const atLastReal  = st.pos === st.total;

    if (delta > 0 && atLastReal) {
      // 마지막 실제 → 오른쪽 → firstClone 으로 "한 칸" 이동
      st.idx = 0;           // 다음에 보여줄 실제 인덱스 (1번)
      st.pos = st.total + 1; // firstClone 위치
      track.style.transition = TRANSITION;
      applyTransform(track, st.pos);
      updatePage(trackId, pageId);
      return;
    }

    if (delta < 0 && atFirstReal) {
      // 첫 실제 → 왼쪽 → lastClone 으로 "한 칸" 이동
      st.idx = st.total - 1; // 다음에 보여줄 실제 인덱스 (마지막)
      st.pos = 0;            // lastClone 위치
      track.style.transition = TRANSITION;
      applyTransform(track, st.pos);
      updatePage(trackId, pageId);
      return;
    }

    // 일반 이동(중간에서는 그대로 한 칸)
    st.idx = (st.idx + delta + st.total) % st.total;
    st.pos += delta;
    track.style.transition = TRANSITION;
    applyTransform(track, st.pos);
    updatePage(trackId, pageId);
  }
})();
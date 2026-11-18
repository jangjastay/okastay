/* 공통: 객실 필터, 사진 크게 보기, 유튜브 */
(function () {
  // 객실 필터
  document.querySelectorAll('.filters').forEach(function (bar) {
    var grid = bar.parentElement.querySelector('[data-filter-grid]');
    if (!grid) return;
    bar.addEventListener('click', function (ev) {
      var b = ev.target.closest('.chip'); if (!b) return;
      bar.querySelectorAll('.chip').forEach(function (c) { c.classList.toggle('on', c === b); });
      var f = b.dataset.f;
      grid.querySelectorAll('.card').forEach(function (c) {
        c.hidden = (c.dataset.filter || '').split(' ').indexOf(f) < 0;
      });
    });
  });

  // 사진 크게 보기 (같은 묶음 안에서 좌우 넘기기)
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest('[data-full]'); if (!t) return;
    var grp = t.closest('[data-group]');
    var list = grp ? [].slice.call(grp.querySelectorAll('[data-full]')) : [t];
    var i = list.indexOf(t);
    var box = document.createElement('div');
    box.className = 'lightbox'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', '사진 크게 보기');
    var im = new Image(); box.appendChild(im);
    var cnt = document.createElement('div'); cnt.className = 'lb-count'; box.appendChild(cnt);
    function show(n) { i = (n + list.length) % list.length; im.src = list[i].dataset.full; im.alt = (list[i].querySelector('img') || {}).alt || ''; cnt.textContent = (i + 1) + ' / ' + list.length; }
    if (list.length > 1) {
      ['prev', 'next'].forEach(function (d) {
        var b = document.createElement('button'); b.className = 'lb-nav ' + d; b.textContent = d === 'prev' ? '‹' : '›';
        b.setAttribute('aria-label', d === 'prev' ? '이전 사진' : '다음 사진');
        b.addEventListener('click', function (e) { e.stopPropagation(); show(i + (d === 'prev' ? -1 : 1)); });
        box.appendChild(b);
      });
    }
    var sx = null;
    box.addEventListener('touchstart', function (e) { sx = e.touches[0].clientX; }, { passive: true });
    box.addEventListener('touchend', function (e) { if (sx === null) return; var dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) { show(i + (dx < 0 ? 1 : -1)); sx = null; e.preventDefault(); } sx = null; });
    var close = function () { box.remove(); document.removeEventListener('keydown', key); };
    var key = function (e) { if (e.key === 'Escape') close(); if (e.key === 'ArrowRight') show(i + 1); if (e.key === 'ArrowLeft') show(i - 1); };
    box.addEventListener('click', function (e) { if (e.target === box || e.target === im) close(); });
    document.addEventListener('keydown', key);
    show(i); document.body.appendChild(box);
  });

  // 옆으로 넘기기 화살표
  document.querySelectorAll('.sw').forEach(function (sw) {
    var tr = sw.querySelector('.sw-track');
    sw.querySelectorAll('.sw-nav').forEach(function (b) {
      b.addEventListener('click', function () { tr.scrollBy({ left: (b.classList.contains('prev') ? -1 : 1) * tr.clientWidth * 0.8 }); });
    });
  });

  // 유튜브 (클릭할 때만 불러옴)
  document.querySelectorAll('.video[data-yt]').forEach(function (v) {
    v.addEventListener('click', function () {
      v.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + v.dataset.yt +
        '?autoplay=1&rel=0" title="오카맨션 소개 영상" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
    }, { once: true });
  });
})();
/* 공간 둘러보기: 파란 점 + 링크 복사 */
(function () {
  document.querySelectorAll('.hs-photo').forEach(function (box) {
    box.addEventListener('click', function (ev) {
      var b = ev.target.closest('.hs'); if (!b) return;
      ev.preventDefault();
      var pop = box.querySelector('#hs-pop-' + b.dataset.hs);
      var open = !pop.hidden;
      box.querySelectorAll('.hs-pop').forEach(function (p) { p.hidden = true; });
      box.querySelectorAll('.hs').forEach(function (x) { x.classList.remove('on'); });
      if (open) return;
      pop.classList.toggle('top', parseFloat(b.style.top) > 55);
      pop.hidden = false; b.classList.add('on');
    });
  });
  document.addEventListener('click', function (ev) {
    var c = ev.target.closest('[data-copy]'); if (!c) return;
    try { navigator.clipboard.writeText(c.dataset.copy); c.textContent = '복사됨'; } catch (e) { prompt('링크', c.dataset.copy); }
  });
})();

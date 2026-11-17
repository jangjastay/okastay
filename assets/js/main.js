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

  // 사진 크게 보기
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest('[data-full]'); if (!t) return;
    var box = document.createElement('div');
    box.className = 'lightbox'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', '사진 크게 보기');
    var im = new Image(); im.src = t.dataset.full; im.alt = (t.querySelector('img') || {}).alt || '';
    box.appendChild(im);
    var close = function () { box.remove(); document.removeEventListener('keydown', esc); };
    var esc = function (e) { if (e.key === 'Escape') close(); };
    box.addEventListener('click', close); document.addEventListener('keydown', esc);
    document.body.appendChild(box);
  });

  // 유튜브 (클릭할 때만 불러옴)
  document.querySelectorAll('.video[data-yt]').forEach(function (v) {
    v.addEventListener('click', function () {
      v.innerHTML = '<iframe src="https://www.youtube-nocookie.com/embed/' + v.dataset.yt +
        '?autoplay=1&rel=0" title="오카맨션 소개 영상" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>';
    }, { once: true });
  });
})();

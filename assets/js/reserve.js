/* 예약 신청: 달력 · 요금 계산 · 전송 */
(function () {
  var C = window.OKA, P = C.policy;
  var form = document.getElementById('rsv'); if (!form) return;
  var fab = document.querySelector('.fab'); if (fab) fab.style.display = 'none';
  var $ = function (n) { return form.elements[n]; };
  var won = function (n) { return n.toLocaleString('ko-KR') + '원'; };
  var pad = function (n) { return (n < 10 ? '0' : '') + n; };
  var iso = function (d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };
  var parse = function (s) { var a = s.split('-'); return new Date(+a[0], a[1] - 1, +a[2]); };
  var addDays = function (d, n) { var x = new Date(d); x.setDate(x.getDate() + n); return x; };
  var DOW = ['일', '월', '화', '수', '목', '금', '토'];
  var fmt = function (d) { return (d.getMonth() + 1) + '월 ' + d.getDate() + '일(' + DOW[d.getDay()] + ')'; };

  var today = new Date(); today.setHours(0, 0, 0, 0);
  var maxDay = addDays(today, 31 * (P.booking_months_ahead || 6));
  var state = { start: null, end: null, view: new Date(today.getFullYear(), today.getMonth(), 1), blocked: { rooms: {}, day: {} } };

  // ---- URL로 넘어온 값 채우기 ----
  var q = new URLSearchParams(location.search);
  ['type', 'with'].forEach(function (k) {
    var v = q.get(k); if (!v) return;
    var el = form.querySelector('input[name=' + k + '][value=' + v + ']'); if (el) el.checked = true;
  });
  if (q.get('room')) $('room').value = q.get('room');
  if (q.get('product')) $('product').value = q.get('product');
  if (q.get('with') === 'kids') { $('dogs').value = 0; $('kids').value = 1; }

  var mode = function () { return form.querySelector('input[name=type]:checked').value; };
  var room = function () { return C.rooms.filter(function (r) { return r.slug === $('room').value; })[0]; };
  var product = function () { return C.dayProducts.filter(function (p) { return p.slug === $('product').value; })[0]; };

  // ---- 예약 불가 날짜 불러오기 (구글 시트) ----
  if (C.appsScriptUrl) {
    fetch(C.appsScriptUrl + '?action=avail').then(function (r) { return r.json(); })
      .then(function (j) { state.blocked = j; drawCal(); })
      .catch(function () { /* 실패해도 신청은 받음 — 숙소가 확인 후 연락 */ });
  }
  var blockedSet = function () {
    var b = mode() === 'stay' ? (state.blocked.rooms || {})[$('room').value] : (state.blocked.day || {})[$('product').value];
    return new Set(b || []);
  };

  // ---- 달력 ----
  var cal = document.getElementById('cal');
  function drawCal() {
    var v = state.view, y = v.getFullYear(), m = v.getMonth();
    var first = new Date(y, m, 1).getDay(), days = new Date(y, m + 1, 0).getDate();
    var bl = blockedSet();
    var h = '<div class="cal-head"><button type="button" data-nav="-1" aria-label="이전 달"' +
      (y === today.getFullYear() && m === today.getMonth() ? ' disabled' : '') + '>‹</button><b>' + y + '년 ' + (m + 1) + '월</b>' +
      '<button type="button" data-nav="1" aria-label="다음 달"' + (new Date(y, m + 1, 1) > maxDay ? ' disabled' : '') + '>›</button></div><div class="cal-grid">';
    DOW.forEach(function (d) { h += '<span class="dow">' + d + '</span>'; });
    for (var i = 0; i < first; i++) h += '<span></span>';
    for (var d = 1; d <= days; d++) {
      var dt = new Date(y, m, d), s = iso(dt), cls = '', dis = false;
      if (dt < today || dt > maxDay) { dis = true; cls = 'past'; }
      else if (bl.has(s)) dis = true;
      if (state.start && s === iso(state.start)) cls += ' sel';
      if (state.end && s === iso(state.end)) cls += ' end';
      if (state.start && state.end && dt > state.start && dt < state.end) cls += ' mid';
      h += '<button type="button" data-d="' + s + '" class="' + cls + '"' + (dis ? ' disabled' : '') +
        ' aria-label="' + fmt(dt) + (bl.has(s) ? ' 마감' : '') + '">' + d + '</button>';
    }
    cal.innerHTML = h + '</div>';
  }
  cal.addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (!b || b.disabled) return;
    if (b.dataset.nav) { state.view = new Date(state.view.getFullYear(), state.view.getMonth() + (+b.dataset.nav), 1); return drawCal(); }
    var d = parse(b.dataset.d);
    if (mode() === 'day') { state.start = d; state.end = null; }
    else if (!state.start || state.end || d <= state.start) { state.start = d; state.end = null; }
    else {
      // 사이에 마감일이 있으면 막기 (체크아웃 날은 마감이어도 됨)
      var bl = blockedSet();
      for (var x = addDays(state.start, 1); x < d; x = addDays(x, 1)) {
        if (bl.has(iso(x))) { state.start = d; state.end = null; drawCal(); return calc(); }
      }
      state.end = d;
    }
    drawCal(); calc();
  });

  // ---- 요금 계산 ----
  var hol = new Set(P.holidays || []);
  function nightKind(d) {
    var s = iso(d);
    var peak = (P.peak_ranges || []).some(function (r) { return s >= r[0] && s <= r[1]; });
    if (peak) return 'peak';
    if ((P.weekend_nights || [6]).indexOf(d.getDay()) >= 0) return 'weekend';
    if (P.holiday_eves_are_weekend && hol.has(iso(addDays(d, 1)))) return 'weekend';
    return 'weekday';
  }
  var KIND = { weekday: '평일', weekend: '주말·공휴일 전날', peak: '성수기' };

  function calc() {
    var rows = [], total = 0, unknown = false, notes = [];
    var n = function (k) { return Math.max(0, parseInt($(k).value, 10) || 0); };
    var adults = n('adults'), kids = n('kids'), dogs = n('dogs'), big = n('bigdogs');
    var dt = document.getElementById('dateText');

    if (mode() === 'stay') {
      var r = room();
      $('bigdogs').disabled = !r.large_dog;
      if (!r.large_dog && big) { $('bigdogs').value = 0; big = 0; }
      if (!state.start) dt.textContent = '체크인 날짜를 골라주세요.';
      else if (!state.end) dt.textContent = fmt(state.start) + ' 체크인 — 체크아웃 날짜를 골라주세요.';
      else {
        var nights = Math.round((state.end - state.start) / 864e5);
        dt.textContent = fmt(state.start) + ' ~ ' + fmt(state.end) + ' · ' + nights + '박';
        var count = { weekday: 0, weekend: 0, peak: 0 };
        for (var x = new Date(state.start); x < state.end; x = addDays(x, 1)) count[nightKind(x)]++;
        Object.keys(count).forEach(function (k) {
          if (!count[k]) return;
          var p = r.price[k];
          if (p) { rows.push([r.name + ' ' + KIND[k] + ' ' + count[k] + '박', won(p * count[k])]); total += p * count[k]; }
          else { rows.push([r.name + ' ' + KIND[k] + ' ' + count[k] + '박', '확인 후 안내']); unknown = true; }
        });
        if (r.base) {
          var extra = Math.max(0, adults + kids - r.base);
          if (r.max && adults + kids > r.max) notes.push('최대 ' + r.max + '인까지 이용할 수 있어요.');
          if (extra) { rows.push(['추가 인원 ' + extra + '명 × ' + nights + '박', won(extra * P.extra_person_fee * nights)]); total += extra * P.extra_person_fee * nights; }
        } else if (adults + kids > 2) { rows.push(['추가 인원', '확인 후 안내']); unknown = true; }
        if (dogs) { rows.push(['반려견 ' + dogs + '마리', won(dogs * P.pet_fee)]); total += dogs * P.pet_fee; }
        if (big) { rows.push(['대형견 ' + big + '마리 (사전 문의)', won(big * P.large_dog_fee)]); total += big * P.large_dog_fee; }
      }
      if (dogs > 2) notes.push('12kg 미만 소형견은 2마리까지 가능해요.');
      if (!r.large_dog) notes.push('대형견은 301호에서만 가능해요.');
    } else {
      var p = product();
      $('bigdogs').disabled = false;
      dt.textContent = state.start ? fmt(state.start) + ' 당일 이용' : '이용 날짜를 골라주세요.';
      if (state.start) {
        if (p.price) { rows.push([p.name, won(p.price)]); total += p.price; }
        else { rows.push([p.name + ' (' + p.price_text + ')', '확인 후 안내']); unknown = true; }
        if (dogs + big) notes.push('당일 이용 반려견 동반 요금은 확인 연락 때 안내드려요.');
        if (!C.dayPriceConfirmed) notes.push('당일 요금은 현재 게시 금액 기준이에요.');
      }
    }
    // 옵션
    var fireAsProduct = mode() === 'day' && $('product').value === 'fire';
    form.querySelectorAll('input[name=addons]').forEach(function (cb) {
      cb.disabled = fireAsProduct && cb.value === 'fire';
      if (cb.disabled) cb.checked = false;
      if (cb.checked && state.start) {
        var a = C.addons.filter(function (x) { return x.id === cb.value; })[0];
        rows.push([a.name, won(a.price)]); total += a.price;
      }
    });

    document.getElementById('sum').innerHTML = rows.map(function (r) { return '<tr><th>' + r[0] + '</th><td>' + r[1] + '</td></tr>'; }).join('') ||
      '<tr><td colspan=2 class="note">날짜를 고르면 금액이 계산돼요.</td></tr>';
    document.getElementById('total').textContent = rows.length ? (unknown ? won(total) + ' + 확인 후 안내' : won(total)) : '-';
    document.getElementById('sumNote').textContent = notes.join(' ');
    state.summary = rows; state.total = total; state.unknown = unknown;
  }

  function setMode() {
    form.parentElement.dataset.mode = mode();
    $('room').required = mode() === 'stay';
    if (mode() === 'day' && state.end) state.end = null;
    drawCal(); calc();
  }
  form.addEventListener('change', function (ev) {
    if (ev.target.name === 'type') setMode();
    else if (ev.target.name === 'room' || ev.target.name === 'product') { state.start = state.end = null; drawCal(); calc(); }
    else calc();
  });
  form.addEventListener('input', calc);

  // ---- 전송 ----
  var res = document.getElementById('result'), btn = document.getElementById('submitBtn');
  function show(html, err) { res.hidden = false; res.className = 'result' + (err ? ' err' : ''); res.innerHTML = html; res.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if ($('website').value) return; // 스팸봇
    var stay = mode() === 'stay';
    if (!state.start || (stay && !state.end)) return show(stay ? '체크인·체크아웃 날짜를 골라주세요.' : '이용 날짜를 골라주세요.', true);
    if (!$('name').value.trim()) return show('예약자 이름을 적어주세요.', true);
    if (!/^0\d{1,2}-?\d{3,4}-?\d{4}$/.test($('phone').value.replace(/\s/g, ''))) return show('휴대폰 번호를 확인해주세요.', true);
    if (!$('agree').checked) return show('개인정보 수집·이용과 환불 규정에 동의해주세요.', true);

    var addons = [].slice.call(form.querySelectorAll('input[name=addons]:checked')).map(function (c) {
      return C.addons.filter(function (a) { return a.id === c.value; })[0].name;
    });
    var data = {
      type: stay ? '숙박' : '당일',
      item: stay ? room().name : product().name,
      itemId: stay ? $('room').value : $('product').value,
      checkin: iso(state.start), checkout: stay ? iso(state.end) : '',
      time: stay ? '' : $('time').value,
      with: form.querySelector('input[name=with]:checked').value,
      adults: $('adults').value, kids: $('kids').value, infants: $('infants').value,
      dogs: $('dogs').value, bigdogs: $('bigdogs').value,
      addons: addons.join(', '), name: $('name').value.trim(), phone: $('phone').value.trim(), memo: $('memo').value.trim(),
      estimate: state.unknown ? won(state.total) + ' + 확인 후 안내' : won(state.total),
      page: location.href
    };
    var text = '[오카맨션 예약 신청]\n' + data.type + ' · ' + data.item + '\n' + data.checkin + (data.checkout ? ' ~ ' + data.checkout : '') +
      (data.time ? ' ' + data.time : '') + '\n성인 ' + data.adults + ' / 어린이 ' + data.kids + ' / 36개월 미만 ' + data.infants +
      ' / 소형견 ' + data.dogs + ' / 대형견 ' + data.bigdogs + (data.addons ? '\n옵션: ' + data.addons : '') +
      '\n예상 금액: ' + data.estimate + '\n' + data.name + ' ' + data.phone + (data.memo ? '\n요청: ' + data.memo : '');

    if (!C.appsScriptUrl) {
      // 시트 연결 전: 문자·카카오톡으로 신청 내용 보내기
      var links = '';
      if (C.phone) links += '<a class="btn block" href="sms:' + C.phone + '?body=' + encodeURIComponent(text) + '">문자로 신청 보내기</a>';
      if (C.kakao) links += '<a class="btn ghost block" style="margin-top:8px" href="' + C.kakao + '" target="_blank" rel="noopener">카카오톡으로 문의</a>';
      return show('<b>아래 내용을 숙소로 보내주세요.</b><pre style="white-space:pre-wrap;font:inherit;font-size:.9rem">' +
        text.replace(/</g, '&lt;') + '</pre>' + (links || '<p class="note">연락처 준비 중입니다.</p>'));
    }

    btn.disabled = true; btn.textContent = '보내는 중…';
    var body = JSON.stringify(data);
    var done = function () {
      btn.textContent = '신청 완료';
      show('<b>예약 신청이 접수됐어요.</b><br>빈 객실을 확인해 <b>' + data.phone + '</b>로 연락드릴게요. 안내받은 계좌로 입금하시면 예약이 확정됩니다.');
    };
    fetch(C.appsScriptUrl, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: body })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok) return done();
        btn.disabled = false; btn.textContent = '예약 신청하기';
        show(j.message || '이미 마감된 날짜가 포함돼 있어요. 다른 날짜를 골라주세요.', true);
      })
      .catch(function () {
        // 응답을 못 읽는 환경 대비 — no-cors로 한 번 더 보내고 접수로 안내
        fetch(C.appsScriptUrl, { method: 'POST', mode: 'no-cors', body: body }).then(done).catch(function () {
          btn.disabled = false; btn.textContent = '예약 신청하기';
          show('전송에 실패했어요. 잠시 후 다시 시도하거나 전화로 문의해주세요.', true);
        });
      });
  });

  setMode();
})();

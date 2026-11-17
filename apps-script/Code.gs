/**
 * 오카맨션 예약 신청 저장소 (구글 스프레드시트 + Apps Script)
 *
 * 하는 일
 *  1) 홈페이지 예약 신청을 '예약신청' 시트에 한 줄씩 저장하고 사장님께 메일 알림
 *  2) 홈페이지 달력에 마감 날짜를 알려줌  (예약신청 + 막기 시트 + 에어비앤비 iCal)
 *  3) 에어비앤비가 가져갈 수 있도록 홈페이지 확정 예약을 iCal로 내보냄
 *
 * 설치 방법은 docs/SETUP.md 의 "4. 예약 신청 시트 연결" 참고.
 */

var NOTIFY_EMAIL = '';            // 비우면 시트 주인 메일로 알림
var SHEET_REQ = '예약신청';
var SHEET_BLOCK = '막기';
var SHEET_ICAL = 'iCal';
var SHEET_ICAL_CACHE = 'iCal가져옴';
var HEAD_REQ = ['접수시각', '상태', '구분', '객실/상품', 'ID', '체크인', '체크아웃', '시간', '동반', '성인', '어린이', '36개월미만',
  '소형견', '대형견', '옵션', '이름', '연락처', '요청사항', '예상금액', '관리메모', '문자발송'];
var SHEET_SET = '설정';
var STATUS = ['신청', '입금대기', '확정', '취소'];

/** 시트 찾기: 시트에서 연 스크립트면 그 시트, 따로 만든 스크립트면 '오카맨션 예약' 시트를 새로 만들어 기억 */
function book_() {
  var ss = SpreadsheetApp.getActive();
  if (ss) return ss;
  var props = PropertiesService.getScriptProperties(), id = props.getProperty('SHEET_ID');
  if (id) return SpreadsheetApp.openById(id);
  ss = SpreadsheetApp.create('오카맨션 예약');
  props.setProperty('SHEET_ID', ss.getId());
  return ss;
}

/** 처음 한 번 실행: 시트와 머리글, 30분마다 에어비앤비 동기화 예약을 만든다 */
function setup() {
  var ss = book_();
  ensure_(ss, SHEET_REQ, HEAD_REQ);
  ensure_(ss, SHEET_BLOCK, ['ID(객실/상품)', '시작일', '종료일(체크아웃일, 비우면 하루)', '사유(야놀자·여기어때·네이버·전화 등)']);
  ensure_(ss, SHEET_ICAL, ['ID(객실)', '에어비앤비 iCal 주소']);
  ensure_(ss, SHEET_ICAL_CACHE, ['ID', '날짜', '가져온 시각']);
  var set = ensure_(ss, SHEET_SET, ['항목', '값', '설명']);
  var have = {}; set.getDataRange().getValues().forEach(function (r) { have[r[0]] = 1; });
  SETTINGS_.forEach(function (r) { if (!have[r[0]]) set.appendRow(r); });
  var reqSh = ss.getSheetByName(SHEET_REQ);
  if (!reqSh.getRange(1, 21).getValue()) reqSh.getRange(1, 21).setValue('문자발송').setFontWeight('bold');
  var req = ss.getSheetByName(SHEET_REQ);
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(STATUS, true).build();
  req.getRange('B2:B').setDataValidation(rule);
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'syncIcal') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('syncIcal').timeBased().everyMinutes(30).create();
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'onStatusEdit') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('onStatusEdit').forSpreadsheet(ss).onEdit().create();
  var s1 = ss.getSheetByName('Sheet1') || ss.getSheetByName('시트1');
  if (s1 && ss.getSheets().length > 1 && s1.getLastRow() === 0) ss.deleteSheet(s1);
  Logger.log('예약 시트 주소: ' + ss.getUrl());
}

function ensure_(ss, name, head) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0) { sh.appendRow(head); sh.setFrozenRows(1); sh.getRange(1, 1, 1, head.length).setFontWeight('bold'); }
  return sh;
}

function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function d_(v) {
  if (v instanceof Date) return Utilities.formatDate(v, 'Asia/Seoul', 'yyyy-MM-dd');
  return String(v || '').trim().replace(/\./g, '-').slice(0, 10);
}
function nextDay_(s) { var d = new Date(s + 'T00:00:00+09:00'); d.setDate(d.getDate() + 1); return d_(d); }
function nights_(from, to) { // from 포함, to 미포함
  var out = [], s = from; if (!to || to <= from) to = nextDay_(from);
  for (var i = 0; s < to && i < 400; i++) { out.push(s); s = nextDay_(s); }
  return out;
}

/** 날짜별 마감 목록 { rooms: {id:[날짜]}, day: {id:[날짜]} } */
function blocked_() {
  var ss = book_(), rooms = {}, day = {};
  var add = function (bag, id, dates) { bag[id] = bag[id] || {}; dates.forEach(function (x) { bag[id][x] = 1; }); };
  var req = ss.getSheetByName(SHEET_REQ).getDataRange().getValues().slice(1);
  req.forEach(function (r) {
    if (r[1] === '취소') return;
    if (r[2] === '숙박') add(rooms, r[4], nights_(d_(r[5]), d_(r[6])));
  });
  ss.getSheetByName(SHEET_BLOCK).getDataRange().getValues().slice(1).forEach(function (r) {
    if (!r[0] || !r[1]) return;
    var id = String(r[0]).trim(), ds = nights_(d_(r[1]), r[2] ? d_(r[2]) : '');
    add(rooms, id, ds); add(day, id, ds);
  });
  ss.getSheetByName(SHEET_ICAL_CACHE).getDataRange().getValues().slice(1).forEach(function (r) { if (r[0]) add(rooms, r[0], [d_(r[1])]); });
  var flat = function (bag) { var o = {}; Object.keys(bag).forEach(function (k) { o[k] = Object.keys(bag[k]).sort(); }); return o; };
  return { rooms: flat(rooms), day: flat(day), updated: new Date().toISOString() };
}

function doGet(e) {
  var a = (e && e.parameter.action) || 'avail';
  if (a === 'ical') return icalOut_(e.parameter.room);
  return json_(blocked_());
}

function doPost(e) {
  var lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    var d = JSON.parse(e.postData.contents);
    if (!d.name || !d.phone || !d.checkin) return json_({ ok: false, message: '필수 항목이 비었어요.' });
    var sh = book_().getSheetByName(SHEET_REQ);
    // 같은 사람이 10분 안에 같은 날짜로 다시 보낸 것은 한 번만 저장
    var rows = sh.getDataRange().getValues().slice(1), now = new Date();
    for (var i = rows.length - 1; i >= 0 && i >= rows.length - 30; i--) {
      var r = rows[i];
      if (r[16] === d.phone && d_(r[5]) === d.checkin && r[4] === d.itemId && now - new Date(r[0]) < 600000) return json_({ ok: true, dup: true });
    }
    if (d.type === '숙박') {
      var bl = (blocked_().rooms[d.itemId] || []);
      var clash = nights_(d.checkin, d.checkout).filter(function (x) { return bl.indexOf(x) >= 0; });
      if (clash.length) return json_({ ok: false, message: clash.join(', ') + ' 은(는) 이미 마감됐어요. 다른 날짜나 객실을 골라주세요.' });
    }
    var withMap = { kids: '아이', pet: '반려견', all: '가족 모두' };
    sh.appendRow([now, '신청', d.type, d.item, d.itemId, d.checkin, d.checkout || '', d.time || '', withMap[d.with] || d.with,
      +d.adults || 0, +d.kids || 0, +d.infants || 0, +d.dogs || 0, +d.bigdogs || 0, d.addons || '', d.name, "'" + d.phone, d.memo || '', d.estimate || '', '']);
    try { notifyGuest_(sh, sh.getLastRow(), '신청'); } catch (e2) { }
    var to = NOTIFY_EMAIL || Session.getEffectiveUser().getEmail();
    if (to) MailApp.sendEmail(to, '[오카맨션] 새 예약 신청 — ' + d.name + ' ' + d.checkin + ' ' + d.item,
      [d.type + ' · ' + d.item, d.checkin + (d.checkout ? ' ~ ' + d.checkout : '') + ' ' + (d.time || ''),
        '성인 ' + d.adults + ' / 어린이 ' + d.kids + ' / 36개월 미만 ' + d.infants + ' / 소형견 ' + d.dogs + ' / 대형견 ' + d.bigdogs,
        '옵션: ' + (d.addons || '-'), '예상 금액: ' + d.estimate, d.name + ' ' + d.phone, '요청: ' + (d.memo || '-'),
        '', '→ 시트에서 날짜 확인 → 상태를 "입금대기"로 바꾸면 계좌 안내 문자 자동 발송 → 입금 확인 후 "확정"으로 바꾸면 확정 문자 자동 발송'].join('\n'));
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, message: '접수 중 오류가 났어요. 전화로 문의해주세요.' });
  } finally { lock.releaseLock(); }
}

/** 에어비앤비 iCal → 'iCal가져옴' 시트 (30분마다 자동) */
function syncIcal() {
  var ss = book_(), out = [], stamp = new Date();
  ss.getSheetByName(SHEET_ICAL).getDataRange().getValues().slice(1).forEach(function (r) {
    var id = String(r[0] || '').trim(), url = String(r[1] || '').trim();
    if (!id || !url) return;
    try {
      var txt = UrlFetchApp.fetch(url, { muteHttpExceptions: true }).getContentText();
      txt.split('BEGIN:VEVENT').slice(1).forEach(function (ev) {
        var s = (ev.match(/DTSTART(?:;VALUE=DATE)?:(\d{8})/) || [])[1], en = (ev.match(/DTEND(?:;VALUE=DATE)?:(\d{8})/) || [])[1];
        if (!s) return;
        var f = function (x) { return x.slice(0, 4) + '-' + x.slice(4, 6) + '-' + x.slice(6, 8); };
        nights_(f(s), en ? f(en) : '').forEach(function (x) { out.push([id, x, stamp]); });
      });
    } catch (e) { /* 한 숙소 실패해도 나머지 진행 */ }
  });
  var c = ss.getSheetByName(SHEET_ICAL_CACHE);
  if (c.getLastRow() > 1) c.getRange(2, 1, c.getLastRow() - 1, 3).clearContent();
  if (out.length) c.getRange(2, 1, out.length, 3).setValues(out);
}

/** 홈페이지 확정 예약 → 에어비앤비 '캘린더 가져오기'에 넣을 주소: 웹앱주소?action=ical&room=객실ID */
function icalOut_(room) {
  var rows = book_().getSheetByName(SHEET_REQ).getDataRange().getValues().slice(1);
  var ev = rows.filter(function (r) { return r[2] === '숙박' && r[4] === room && r[1] !== '취소'; }).map(function (r, i) {
    var s = d_(r[5]).replace(/-/g, ''), en = d_(r[6] || nextDay_(d_(r[5]))).replace(/-/g, '');
    return ['BEGIN:VEVENT', 'UID:okastay-' + room + '-' + s + '-' + i + '@okastay.kr', 'DTSTAMP:' + s + 'T000000Z',
      'DTSTART;VALUE=DATE:' + s, 'DTEND;VALUE=DATE:' + en, 'SUMMARY:Reserved (okastay.kr)', 'END:VEVENT'].join('\r\n');
  });
  var cal = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//okastay.kr//KO', 'CALSCALE:GREGORIAN'].concat(ev, ['END:VCALENDAR']).join('\r\n');
  return ContentService.createTextOutput(cal).setMimeType(ContentService.MimeType.ICAL);
}


/* ===================== 손님 자동 카카오 알림톡 (솔라피) ===================== */

var SETTINGS_ = [
  ['솔라피 API Key', '', 'solapi.com → 개발/연동 → API Key 관리'],
  ['솔라피 API Secret', '', '위와 같은 화면에서 발급'],
  ['카카오 채널 ID(pfId)', '', '솔라피 → 카카오 채널 연동 후 나오는 pfId (KA01PF…)'],
  ['발신번호', '', '솔라피에 등록한 번호 (솔라피가 요구하는 경우만)'],
  ['입금계좌', '', '예: 농협 000-0000-0000-00 장자스테이(주)'],
  ['입금기한(시간)', '3', '입금대기 알림 보낸 뒤 몇 시간 안에 입금'],
  ['주소', '충청북도 청주시 상당구 미원면 운암옥화길 186-16', '확정 알림에 들어감'],
  ['문의전화', '', '알림 끝에 들어감'],
  ['자동알림 사용', 'N', 'Y로 바꾸면 카카오 알림톡 발송 시작'],
  ['템플릿ID_신청', '', '카카오 심사 통과 후 솔라피에 나오는 템플릿 ID (KA01TP…)'],
  ['템플릿ID_입금대기', '', ''],
  ['템플릿ID_확정', '', ''],
  ['템플릿ID_취소', '', '']
];

function settings_() {
  var o = {}, sh = book_().getSheetByName(SHEET_SET);
  if (!sh) return o;
  sh.getDataRange().getValues().slice(1).forEach(function (r) { if (r[0]) o[String(r[0]).trim()] = r[1]; });
  return o;
}

/** 상태 칸(B열)을 바꾸면 실행 (설치형 트리거) */
function onStatusEdit(e) {
  var sh = e.range.getSheet();
  if (sh.getName() !== SHEET_REQ || e.range.getColumn() !== 2 || e.range.getRow() < 2) return;
  for (var i = 0; i < e.range.getNumRows(); i++) {
    var row = e.range.getRow() + i, st = String(sh.getRange(row, 2).getValue()).trim();
    if (st && st !== '신청') notifyGuest_(sh, row, st);
  }
}

function notifyGuest_(sh, row, status) {
  var S = settings_();
  if (String(S['자동알림 사용']).toUpperCase() !== 'Y') return;
  var tid = String(S['템플릿ID_' + status] || '').trim(); if (!tid) return;
  var r = sh.getRange(row, 1, 1, 21).getValues()[0];
  var log = String(r[20] || '');
  if (log.indexOf(status + ' ') >= 0) return; // 같은 상태 알림은 한 번만
  var phone = String(r[16]).replace(/[^0-9]/g, '');
  if (!/^01\d{8,9}$/.test(phone)) return;
  var ci = d_(r[5]), co = r[6] ? d_(r[6]) : '';
  var hours = Number(S['입금기한(시간)']) || 3;
  var due = Utilities.formatDate(new Date(Date.now() + hours * 3600000), 'Asia/Seoul', 'M월 d일 HH:mm');
  var inTime = r[2] === '숙박' ? ({ dokchae2: '17:00', campstay1: '18:00', campstay2: '18:00' }[r[4]] || '15:00') : (r[7] || '예약 시간');
  var amount = String(r[18] || '').trim().replace(/\s*\+\s*확인 후 안내/, '') || '안내드린 금액'; // 예상금액 칸을 최종 금액으로 고쳐 쓰면 그 금액이 나감
  var v = {
    '이름': r[15], '상품': r[3], '날짜': co ? ci + ' ~ ' + co : ci + (r[7] ? ' ' + r[7] : ''),
    '금액': amount, '입금계좌': S['입금계좌'], '입금기한': due, '입실': inTime,
    '주소': S['주소'], '문의전화': S['문의전화']
  };
  var vars = {}; Object.keys(v).forEach(function (k) { vars['#{' + k + '}'] = String(v[k] == null ? '' : v[k]); });
  var res = solapiSend_(S, phone, tid, vars);
  var stamp = Utilities.formatDate(new Date(), 'Asia/Seoul', 'M/d HH:mm');
  sh.getRange(row, 21).setValue((log ? log + ' / ' : '') + status + ' ' + (res.ok ? '카톡발송 ' : '실패(' + res.msg + ') ') + stamp);
}

function solapiSend_(S, to, templateId, vars) {
  try {
    var key = String(S['솔라피 API Key']).trim(), secret = String(S['솔라피 API Secret']).trim(), pfId = String(S['카카오 채널 ID(pfId)']).trim();
    if (!key || !secret || !pfId) return { ok: false, msg: '설정 비어있음' };
    var date = new Date().toISOString(), salt = Utilities.getUuid().replace(/-/g, '');
    var sig = Utilities.computeHmacSha256Signature(date + salt, secret).map(function (b) { return ('0' + (b & 255).toString(16)).slice(-2); }).join('');
    var msg = { to: to, kakaoOptions: { pfId: pfId, templateId: templateId, variables: vars, disableSms: true } };
    var from = String(S['발신번호'] || '').replace(/[^0-9]/g, ''); if (from) msg.from = from;
    var resp = UrlFetchApp.fetch('https://api.solapi.com/messages/v4/send', {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      headers: { Authorization: 'HMAC-SHA256 apiKey=' + key + ', date=' + date + ', salt=' + salt + ', signature=' + sig },
      payload: JSON.stringify({ message: msg })
    });
    var code = resp.getResponseCode();
    if (code >= 200 && code < 300) return { ok: true };
    var j = {}; try { j = JSON.parse(resp.getContentText()); } catch (x) { }
    return { ok: false, msg: j.errorMessage || ('HTTP ' + code) };
  } catch (err) { return { ok: false, msg: String(err).slice(0, 60) }; }
}

/** 설정 확인용: 예약신청 시트 맨 아래 줄 손님에게 '확정' 알림을 시험 발송 (본인 번호로 신청한 줄에서 실행하세요) */
function testKakao() {
  var sh = book_().getSheetByName(SHEET_REQ), row = sh.getLastRow(), S = settings_();
  var r = sh.getRange(row, 1, 1, 21).getValues()[0];
  Logger.log(r[15] + ' ' + r[16] + ' 에게 시험 발송: ' + JSON.stringify(solapiSend_(S, String(r[16]).replace(/[^0-9]/g, ''), String(S['템플릿ID_확정']).trim(),
    { '#{이름}': r[15], '#{상품}': r[3], '#{날짜}': d_(r[5]), '#{입실}': '15:00', '#{주소}': S['주소'], '#{문의전화}': S['문의전화'] })));
}

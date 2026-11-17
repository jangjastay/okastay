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
  '소형견', '대형견', '옵션', '이름', '연락처', '요청사항', '예상금액', '관리메모'];

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
  var req = ss.getSheetByName(SHEET_REQ);
  var rule = SpreadsheetApp.newDataValidation().requireValueInList(['신청', '확정', '취소'], true).build();
  req.getRange('B2:B').setDataValidation(rule);
  ScriptApp.getProjectTriggers().forEach(function (t) { if (t.getHandlerFunction() === 'syncIcal') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('syncIcal').timeBased().everyMinutes(30).create();
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
    var to = NOTIFY_EMAIL || Session.getEffectiveUser().getEmail();
    if (to) MailApp.sendEmail(to, '[오카맨션] 새 예약 신청 — ' + d.name + ' ' + d.checkin + ' ' + d.item,
      [d.type + ' · ' + d.item, d.checkin + (d.checkout ? ' ~ ' + d.checkout : '') + ' ' + (d.time || ''),
        '성인 ' + d.adults + ' / 어린이 ' + d.kids + ' / 36개월 미만 ' + d.infants + ' / 소형견 ' + d.dogs + ' / 대형견 ' + d.bigdogs,
        '옵션: ' + (d.addons || '-'), '예상 금액: ' + d.estimate, d.name + ' ' + d.phone, '요청: ' + (d.memo || '-'),
        '', '→ 시트에서 날짜 확인 후 손님께 문자 → 입금 확인되면 상태를 "확정"으로 바꿔주세요.'].join('\n'));
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

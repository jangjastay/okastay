# 오카맨션 직접예약 홈페이지 — 운영·설정 안내

주소: https://okastay.kr  ·  저장소: jangjastay/okastay

---

## 0. 지금 비어 있는 값 (채우면 사이트에 자동으로 나타남)

모두 `data/site.json` 한 파일에 있습니다. 값을 넣고 `python3 tools/build.py` 를 실행하면(또는 Claude에게 "site.json 이 값으로 바꿔서 다시 올려줘"라고 하면) 전체 페이지가 다시 만들어집니다.

| 항목 | site.json 위치 | 비어 있을 때 사이트 표시 |
|---|---|---|
| 대표 전화번호 | `site.phone` | 전화 버튼 숨김 |
| 카카오톡 채널 주소 | `site.kakao_channel` | 카톡 버튼 숨김 |
| 입금 계좌 | `site.bank` | 이용안내에 계좌 숨김 |
| 대표자·사업자등록번호·통신판매업 번호 | `site.ceo`, `site.biz_no`, `site.mail_order_no` | 하단에 회사명만 표시 |
| 예약 시트 주소 | `site.apps_script_url` | 예약 신청 시 "문자로 보내기" 방식으로 동작 |
| 객실별 요금 (평일·주말·성수기) | `rooms[].price` | "요금 문의 / 확인 후 안내" |
| 객실별 기준·최대 인원 | `rooms[].base`, `rooms[].max` | "인원 확인 후 안내" |
| 성수기 기간 | `policy.peak_ranges` | 성수기 요금 미적용 |
| 당일 요금 확정 여부 | `day_price_confirmed` | `false`면 "현재 게시 금액 기준" 안내문 표시 |
| 실제 후기 | `reviews` | 후기 영역 숨김 |
| 지난 이벤트 소개·사진 | `events` | 이벤트 영역 숨김 |
| 독채 2호 사진 | `rooms[dokchae2].photos` | "사진 준비 중" |

후기 형식: `{"text": "후기 내용", "who": "닉네임", "source": "네이버 리뷰"}` — 실제 후기만.

> **법적 표시**: 홈페이지에서 예약·결제를 받으면 전자상거래법상 하단에 상호·대표자·사업자등록번호·통신판매업 신고번호·주소·연락처를 표시해야 합니다. 통신판매업 신고가 안 돼 있으면 정부24에서 먼저 신고하세요.

### 확인이 필요한 내용 (여기어때 등록 기준으로 넣음)
- 202~207호에도 반려견 동반이 모두 되는지, 캠핑스테이도 반려견 가능한지
- 대형견은 301호만 가능한지
- 환불 규정의 5일 전~2일 전 구간 정확한 비율
- 주말 요금 기준: 지금은 **토요일 밤 + 공휴일 전날**. 금요일도 주말이면 `policy.weekend_nights` 를 `[5,6]` 으로
- 독채 1호 사진: 폴더의 `2026.3.26/오카맨션독채1.jpg`, `오카맨션독채바베큐운동장.jpg` 를 썼습니다. 독채 1호가 맞는지 확인 필요

### 사진 원칙 (적용 완료)
- `F:\오카사진` 에서 실제 촬영본만 골라 1600px로 줄이고 위치정보(EXIF)를 지웠습니다.
- 뺀 사진: AI 생성/합성으로 보이는 것(파일명 remix·assets_task·ChatGPT, 벚꽃여행·봄놀이·독채전용운동장 등), 손님 얼굴이 보이는 것, 토토가·풀파티·야간 행사.
- 폴더의 `오카맨션독채1.png`, `오카맨션독채2.png` 는 실제로는 캠핑스테이 2·1 사진과 같은 사진이라 캠핑스테이에 썼습니다.

---

## 1. GitHub Pages 켜기
1. github.com/jangjastay/okastay → **Settings → Pages**
2. Source: **Deploy from a branch**, Branch: **main / (root)** → Save
3. Custom domain에 `okastay.kr` 입력(저장소에 CNAME 파일이 이미 있어 자동으로 들어가 있을 수 있음)
4. DNS가 연결된 뒤 **Enforce HTTPS** 체크

## 2. 가비아 DNS 설정 (okastay.kr)
가비아 → My가비아 → 도메인 관리 → okastay.kr → **DNS 정보 → DNS 설정**

| 타입 | 호스트 | 값 |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | jangjastay.github.io. |

기존에 가비아 기본 A 레코드(파킹)가 있으면 지웁니다. 반영까지 보통 10분~몇 시간.

## 3. 예약 신청 시트 연결 (구글 스프레드시트)
1. 구글 드라이브에서 새 스프레드시트 만들기 → 이름 "오카맨션 예약"
2. 메뉴 **확장 프로그램 → Apps Script** → 기본 코드를 지우고 `apps-script/Code.gs` 내용을 통째로 붙여넣기 → 저장
3. 위쪽 함수 목록에서 `setup` 선택 → **실행** → 권한 허용 (시트 4개가 생기고 30분마다 에어비앤비 동기화가 예약됨)
4. **배포 → 새 배포 → 유형: 웹 앱** / 실행: **나** / 액세스: **모든 사용자** → 배포
5. 나온 웹 앱 주소(`https://script.google.com/macros/s/…/exec`)를 `site.apps_script_url` 에 넣고 다시 빌드·업로드

시트 사용법
- **예약신청**: 홈페이지 신청이 한 줄씩 쌓임 + 메일 알림. 확인 후 손님께 문자 → 입금되면 `상태`를 **확정**, 안 되면 **취소**. `신청`·`확정` 상태인 날짜는 달력에서 자동 마감.
- **막기**: 야놀자·여기어때·네이버·전화로 팔린 날짜를 적으면 홈페이지 달력에서 마감. `ID` 는 아래 객실 ID.
- **iCal**: 에어비앤비 숙소의 캘린더 내보내기 주소를 적으면 30분마다 자동으로 마감 반영.
- 홈페이지 예약을 에어비앤비로 보내려면: 에어비앤비 캘린더 가져오기에 `웹앱주소?action=ical&room=객실ID` 입력.

객실 ID: `202` `203` `204` `205` `206` `207` `301` `dokchae1` `dokchae2` `campstay1` `campstay2`
당일 상품 ID: `warm-pool` `pool` `deck` `bbq` `fire`

## 4. 중복 예약 막는 운영 원칙
- 객실을 **홈페이지 전용**과 **예약 사이트용**으로 나눠 팝니다. 홈페이지 전용 객실은 다른 사이트에서 닫아두고, 예약 사이트용 객실은 홈페이지 `막기` 시트에 기간 전체를 넣어 닫아둡니다.
- 에어비앤비는 iCal로 자동, 야놀자·여기어때·네이버는 하루 2~3번(오전·오후·저녁) `막기` 시트에 대조 입력.
- 홈페이지 신청은 "신청 → 확인 → 확정 → 입금" 이라 확인 단계에서 한 번 더 걸러집니다.

## 5. 검색 등록
1. **네이버 서치어드바이저** (searchadvisor.naver.com) → 사이트 등록 `https://okastay.kr` → HTML 태그 방식 → content 값을 `site.naver_site_verification` 에 넣고 다시 업로드 → 소유 확인 → 요청 > **사이트맵 제출** `https://okastay.kr/sitemap.xml`
2. **구글 서치 콘솔** (search.google.com/search-console) → URL 접두어 `https://okastay.kr` → HTML 태그 → `site.google_site_verification` → 사이트맵 제출
3. **빙 웹마스터 도구** → 구글 서치 콘솔에서 가져오기
4. **다음 검색 등록** (register.search.daum.net) → 사이트 등록
5. **네이버 스마트플레이스 / 구글 비즈니스 프로필 / 카카오맵**: 각 업체 정보의 홈페이지 칸에 `https://okastay.kr` 입력

## 6. 파일 구조
```
data/site.json      ← 모든 내용(요금·객실·문구·사진 연결)
tools/build.py      ← site.json → HTML 생성
apps-script/Code.gs ← 구글 시트 예약 저장·달력 마감
assets/img/         ← 사진 (xxx.jpg 1600px, xxx-s.jpg 720px)
index.html, rooms/, day/, reserve.html, gallery.html, guide.html  ← 자동 생성
sitemap.xml, robots.txt, CNAME ← 자동 생성
```

# 인터페이스 규격

## 공개 API

`calculate(case: TaxCase) -> CalculationResult`

- 모든 금액은 원(KRW) 단위의 0 이상 정수다.
- `balance_due > 0`이면 예상 납부, `< 0`이면 예상 환급이다.
- `prepayments_income_tax`에는 소득 객체에 이미 담긴 원천징수세액을 중복 입력하면 안 된다.
- `income_deductions`, `tax_credits`, `additional_income_tax`는 호출자가 자격과 한도를 검증한 확정 합계다.
- 단순경비율은 basis point(1% = 100 bps)로 입력한다.

`build_canonical_payload(result, taxpayer_ref=...) -> dict`

- 계산과 신고 포맷 사이의 안정된 중간 표현이다.
- `taxpayer_ref`에 주민등록번호나 이름을 넣지 않는다.

`render_fixed_width(records, spec) -> bytes`

- 국세청 공식 파일설명서로 만든 `FixedWidthSpec`만 받는다.
- 스키마가 없거나 검토되지 않았거나 필드가 넘치면 파일을 만들지 않는다.

## 예외 계약

| 예외 | 의미 | 호출자 처리 |
|---|---|---|
| `ValidationError` | 필수값 누락/형식·범위 오류 | 데이터 정정 |
| `UnsupportedCase` | 안전한 자동계산 범위 밖 | 세무 수동검토 |
| `EFileSpecUnavailable` | 승인된 해당 연도 신고 규격 없음 | 파일 생성 중단 |

## 입력 매핑 시 필수 검토

근로 지급명세서의 총급여·결정세액과 인적용역 지급명세서의 수입금액·국세·지방세를 구분한다. 업종코드, 신규/계속사업자 여부, 직전연도 수입금액, 장부의무, 경비 증빙 상태 없이는 경비율 적용자격을 자동 확정하지 않는다.

# Maintenance Harness

## 목적

정책과 공식 사이트의 변화를 조기에 발견하고, 변경된 규칙이 검토 없이 운영으로 들어가는 것을 막는다. 페이지 변경은 알림 신호일 뿐 세법 변경의 확정 근거가 아니다.

## 정기 실행

```powershell
$env:PYTHONPATH = "src"
python -m krtax.maintenance validate
python -m unittest discover -s tests -v
```

위 검사는 네트워크를 사용하지 않으므로 모든 코드 변경과 CI에서 실행한다.

공식 출처 점검은 네트워크 사용을 명시적으로 허용해야 한다.

```powershell
$env:PYTHONPATH = "src"
python -m krtax.maintenance check --online
```

종료 코드 `0`은 등록된 지문과 일치, `2`는 변경 또는 기준선 누락, `1`은 확인 실패다. 확인 실패를 변경 없음으로 해석하면 안 된다.

## 최초 기준선과 변경 후보

기준선은 자동 덮어쓰지 않는다. 다음 명령으로 검토 후보만 만든다.

```powershell
python -m krtax.maintenance capture --online --output maintenance/candidates/2026-08-04.json
```

담당자가 각 URL의 기관·문서·시행일을 확인한 후 `source-baseline.json` 반영을 승인한다. `maintenance/candidates/`는 Git에서 제외된다.

## 변경 대응 흐름

1. `check`가 변경 또는 기준선 누락을 보고한다.
2. 후보 지문을 캡처하고 공식 페이지의 실제 의미 변경 여부를 확인한다.
3. 정책 영향표에 귀속연도, 계산 필드, 신고 서식, 시행일을 기록한다.
4. 새 규칙/스키마와 경계·골든 테스트를 작성한다.
5. `approved-artifacts.json`의 해시는 세무 검토 이후에만 갱신한다.
6. 전체 harness와 변환검증을 통과한 뒤 운영 규칙 허용목록을 변경한다.

영향 분석은 `change-assessment-template.md`를 복사해 작성한다. 사이트 문구만 바뀌고 정책 의미가 같다면 `rejected`로 종료하되 판단 근거를 남긴다.

## 권장 주기

- 평시: 법령 14일, 국세청 안내 30일
- 12월~신고 종료: 주 1회
- 세법 개정안·시행령 발표 또는 국세청 신고 안내 게시 후: 즉시
- 전자신고 파일설명서 수령 후: 파일 해시 고정 및 매 빌드 검증

실제 스케줄러 구성은 배포 범위 밖이다. CI나 내부 작업 스케줄러는 오프라인 `validate`를 필수 게이트로 하고, 온라인 `check`는 별도 제한 네트워크 작업으로 운영한다.

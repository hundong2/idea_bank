# 기여 가이드

모든 기여는 Apache License 2.0과 프로젝트의 기밀·근거·검증 규칙을 따라야 한다. 작업 전에 `AGENTS.md`, `LICENSE`, `DISCLAIMER.md`를 읽는다.

## 권리와 출처

- 자신이 작성했거나 Apache-2.0으로 제출할 권한이 있는 코드·문서만 기여한다.
- 고객정보, 원 발주자료, 비공개 전자신고 규격, 영업비밀을 포함하지 않는다.
- 제3자 자료를 포함하면 출처, 라이선스, 변경 여부와 필요한 저작권 고지를 함께 제출한다.
- 공식 세법 자료는 긴 원문을 복사하지 말고 필요한 범위로 요약하고 링크·확인일을 기록한다.

## Developer Certificate of Origin

각 커밋에는 Developer Certificate of Origin(DCO) 1.1에 대한 동의를 나타내는 sign-off를 포함한다. DCO는 기여자가 제출 권한을 보유한다는 출처 확인 절차이며 별도의 보증이나 프로젝트 책임 인수가 아니다.

```text
Signed-off-by: Legal Name <email@example.com>
```

Git에서는 다음과 같이 생성할 수 있다.

```bash
git commit -s -m "describe the change"
```

DCO 1.1 원문: https://developercertificate.org/

## 검증과 승인

```powershell
.\scripts\verify.ps1
```

정책·전자신고 변경에는 공식 출처, 적용 귀속연도, 경계값 테스트와 세무 검토가 필요하다. 테스트 통과만으로 운영 활성화를 승인하지 않는다.

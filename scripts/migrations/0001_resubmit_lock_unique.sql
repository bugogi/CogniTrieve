-- 0001_resubmit_lock_unique.sql
-- 목적: 재제출 차단 정책 적용 — step1_responses/step2_responses에
--       session_id 유니크 인덱스를 추가해 세션당 1회 제출만 허용한다.
-- 대상: 이미 테이블이 생성되어 있는 기존 DB(dev, prod 모두). 신규 설치는
--       scripts/schema.sql에 이미 반영되어 있어 이 스크립트가 필요 없다.
--
-- *** 이 스크립트는 dev와 prod Supabase 프로젝트 양쪽에 각각 수동으로
--     실행해야 한다(두 환경 모두 이미 스키마가 적용되어 운영 중이므로,
--     어느 한쪽에도 자동으로 반영되지 않는다). Supabase 대시보드 > SQL
--     Editor에서 프로젝트를 전환해 가며 두 번 실행할 것.
--
-- 주의: 기존에 같은 session_id로 중복 제출된 row가 있으면 아래 유니크
--       인덱스 생성이 실패한다. 먼저 아래 조회로 중복 여부를 확인하고,
--       있다면 정책에 따라(예: 세션당 최신 row만 남기고 정리) 수동으로
--       정리한 뒤 이 스크립트를 실행할 것. 이 스크립트 자체는 중복 데이터를
--       자동으로 삭제하지 않는다.
--
--   select session_id, count(*) from step1_responses group by session_id having count(*) > 1;
--   select session_id, count(*) from step2_responses group by session_id having count(*) > 1;
--
-- 재실행해도 안전함(if not exists).

create unique index if not exists step1_responses_session_id_key on step1_responses(session_id);
create unique index if not exists step2_responses_session_id_key on step2_responses(session_id);
-- step3_responses는 세션당 여러 row(퀴즈별 제출)를 허용하므로 유니크 제약을 걸지 않는다.

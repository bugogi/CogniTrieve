-- CogniTrieve 구현 Phase 1: DB 스키마
-- 출처: docs/10_구현로드맵.md 부록 A
-- 적용 방법: Supabase 대시보드 > SQL Editor에서 dev/prod 프로젝트에 각각 수동 실행.

create extension if not exists pgcrypto;

create table if not exists cases (
  case_id text primary key,           -- 'assignment_A' | 'assignment_B' | 'assignment_C' | 'assignment_D' | 'course' | 'exam_prep'
  learning_type text not null,        -- '과제' | '수강' | '시험 대비'
  output_type text,                   -- 'A' | 'B' | 'C' | 'D' | null
  questions jsonb not null,           -- 5문항 배열
  hotspot_primary int not null,
  hotspot_secondary int not null,
  hotspot_tier jsonb not null,        -- {"primary": "최고위험", "secondary": "위험"}
  concept_vocabulary jsonb            -- Phase 3(2단계 일반화) 전까지는 비워둠
);

create table if not exists sessions (
  session_id uuid primary key default gen_random_uuid(),
  anon_id text not null,              -- UUID 또는 해시된 식별자
  case_id text references cases(case_id),
  consented_at timestamptz,
  created_at timestamptz default now()
);

create table if not exists step1_responses (
  id bigint generated always as identity primary key,
  session_id uuid references sessions(session_id),
  case_id text references cases(case_id),   -- 직접 포함 (집계 편의)
  q1 int, q2 int, q3 int, q4 int, q5 int,
  total_score int,
  persona text,
  created_at timestamptz default now()
);

create table if not exists step2_responses (
  id bigint generated always as identity primary key,
  session_id uuid references sessions(session_id),
  case_id text references cases(case_id),   -- 직접 포함
  health_score numeric,
  components jsonb,                          -- 유형별 세부 점수(항목명 유동적)
  risk_highlight text,
  analysis_summary text,
  created_at timestamptz default now()
);

create table if not exists step3_responses (
  id bigint generated always as identity primary key,
  session_id uuid references sessions(session_id),
  case_id text references cases(case_id),   -- 직접 포함
  quiz_type text,
  dynamic_question text,
  student_answer text,
  is_correct boolean,
  matched_keyword text,
  created_at timestamptz default now()
);

-- RLS: 앱은 항상 service_role key로만 접근한다(Streamlit 서버 사이드 실행, 브라우저에
-- 키가 노출되지 않음). service_role은 RLS를 우회하므로 아래 정책은 "만에 하나 anon
-- key가 잘못 쓰이더라도 아무 것도 할 수 없게" 막는 방어적 이중장치다.
alter table cases enable row level security;
alter table sessions enable row level security;
alter table step1_responses enable row level security;
alter table step2_responses enable row level security;
alter table step3_responses enable row level security;

create policy "service role full access" on cases
  for all using (auth.role() = 'service_role');
create policy "service role full access" on sessions
  for all using (auth.role() = 'service_role');
create policy "service role full access" on step1_responses
  for all using (auth.role() = 'service_role');
create policy "service role full access" on step2_responses
  for all using (auth.role() = 'service_role');
create policy "service role full access" on step3_responses
  for all using (auth.role() = 'service_role');

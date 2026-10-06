CREATE SCHEMA IF NOT EXISTS mini_multi_agent_04;

CREATE TABLE IF NOT EXISTS mini_multi_agent_04.places (
    place_id SERIAL PRIMARY KEY,
    city TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    transit_note TEXT NOT NULL,
    UNIQUE(city, name)
);

ALTER TABLE mini_multi_agent_04.places
    ADD COLUMN IF NOT EXISTS is_indoor BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE mini_multi_agent_04.places
    ADD COLUMN IF NOT EXISTS estimated_cost INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS mini_multi_agent_04.budget_reference (
    city TEXT PRIMARY KEY,
    daily_budget INTEGER NOT NULL CHECK (daily_budget >= 0)
);

CREATE TABLE IF NOT EXISTS mini_multi_agent_04.orders (
    order_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mini_multi_agent_04.support_policies (
    policy_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    policy_text TEXT NOT NULL,
    version INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO mini_multi_agent_04.places (city, name, category, transit_note) VALUES
    ('부산', '영화의전당', '문화', '지하철 센텀시티역 이용'),
    ('부산', '부산시립미술관', '문화', '지하철 벡스코역 이용'),
    ('서울', '국립중앙박물관', '문화', '지하철 이촌역 이용'),
    ('제주', '제주도립미술관', '문화', '버스 정류장 도보 이동')
ON CONFLICT (city, name) DO UPDATE SET
    category = EXCLUDED.category,
    transit_note = EXCLUDED.transit_note;

UPDATE mini_multi_agent_04.places SET is_indoor = TRUE, estimated_cost = CASE
    WHEN name = '부산시립미술관' THEN 10000
    WHEN name = '영화의전당' THEN 15000 ELSE 0 END
WHERE (city, name) IN (('부산', '영화의전당'), ('부산', '부산시립미술관'),
                       ('서울', '국립중앙박물관'), ('제주', '제주도립미술관'));

INSERT INTO mini_multi_agent_04.places
    (city, name, category, transit_note, is_indoor, estimated_cost) VALUES
    ('부산', '광안리해수욕장', '해변', '지하철 광안역 이용', FALSE, 0),
    ('부산', '해운대해수욕장', '해변', '지하철 해운대역 이용', FALSE, 0),
    ('서울', '서울숲', '공원', '지하철 서울숲역 이용', FALSE, 0),
    ('제주', '이호테우해변', '해변', '버스 정류장 도보 이동', FALSE, 0)
ON CONFLICT (city, name) DO UPDATE SET
    category = EXCLUDED.category,
    transit_note = EXCLUDED.transit_note,
    is_indoor = EXCLUDED.is_indoor,
    estimated_cost = EXCLUDED.estimated_cost;

INSERT INTO mini_multi_agent_04.budget_reference (city, daily_budget) VALUES
    ('부산', 200000), ('서울', 230000), ('제주', 250000)
ON CONFLICT (city) DO UPDATE SET daily_budget = EXCLUDED.daily_budget;

INSERT INTO mini_multi_agent_04.orders (order_id, status) VALUES
    ('ORDER-102', '배송 지연')
ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status, updated_at = NOW();

INSERT INTO mini_multi_agent_04.support_policies
    (policy_key, title, policy_text, version, active) VALUES
    ('delivery_delay_refund', '배송 지연 환불 정책', '배송 지연이 확인되면 상담 후 환불을 검토합니다.', 1, TRUE)
ON CONFLICT (policy_key) DO UPDATE SET
    title = EXCLUDED.title,
    policy_text = EXCLUDED.policy_text,
    version = EXCLUDED.version,
    active = TRUE;

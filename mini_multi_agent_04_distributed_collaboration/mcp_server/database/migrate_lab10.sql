ALTER TABLE mini_multi_agent_04.places
    ADD COLUMN IF NOT EXISTS is_indoor BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE mini_multi_agent_04.places
    ADD COLUMN IF NOT EXISTS estimated_cost INTEGER NOT NULL DEFAULT 0;

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

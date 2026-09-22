CREATE SCHEMA IF NOT EXISTS mini_multi_agent_01;
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.refund_policies (policy_id INTEGER PRIMARY KEY, policy_text TEXT NOT NULL, active BOOLEAN NOT NULL DEFAULT TRUE);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.help_articles (topic TEXT PRIMARY KEY, article TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.travel_places (
    place_id INTEGER PRIMARY KEY, city TEXT NOT NULL, name TEXT NOT NULL,
    category TEXT NOT NULL, address TEXT NOT NULL, nearest_station TEXT,
    indoor BOOLEAN NOT NULL, allergy_note TEXT NOT NULL,
    source_url TEXT NOT NULL, verified_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.transit_guides (
    guide_id INTEGER PRIMARY KEY, city TEXT NOT NULL, origin TEXT NOT NULL,
    destination TEXT NOT NULL, transport_type TEXT NOT NULL,
    route_summary TEXT NOT NULL, estimated_minutes INTEGER,
    estimated_fare INTEGER, source_url TEXT NOT NULL, verified_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.allergy_guidance (
    guidance_id INTEGER PRIMARY KEY, city TEXT NOT NULL, title TEXT NOT NULL,
    guidance TEXT NOT NULL, emergency BOOLEAN NOT NULL DEFAULT FALSE,
    source_url TEXT NOT NULL, verified_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.content_facts (
    fact_id INTEGER PRIMARY KEY, topic TEXT NOT NULL, fact TEXT NOT NULL,
    source_url TEXT NOT NULL, verified_at DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS mini_multi_agent_01.quality_requirements (
    requirement_id INTEGER PRIMARY KEY, scenario TEXT NOT NULL,
    requirement_key TEXT NOT NULL, requirement_text TEXT NOT NULL,
    source_url TEXT NOT NULL, verified_at DATE NOT NULL,
    UNIQUE (scenario, requirement_key)
);

INSERT INTO mini_multi_agent_01.orders VALUES ('ORDER-101', '배송 중'), ('ORDER-102', '배송 지연') ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status;
INSERT INTO mini_multi_agent_01.refund_policies VALUES (1, '배송 지연 주문은 상태 확인 후 환불 정책 안내가 가능합니다. 실제 환불은 이 프로젝트에서 실행하지 않습니다.', TRUE) ON CONFLICT (policy_id) DO UPDATE SET policy_text = EXCLUDED.policy_text, active = EXCLUDED.active;
INSERT INTO mini_multi_agent_01.help_articles VALUES ('로그인', '비밀번호 재설정과 계정 잠금 상태를 확인하세요.'), ('결제', '결제 수단과 승인 상태를 확인하세요.') ON CONFLICT (topic) DO UPDATE SET article = EXCLUDED.article;

INSERT INTO mini_multi_agent_01.travel_places VALUES
    (1, '부산', '국립해양박물관', '박물관', '부산광역시 영도구 해양로301번길 45', '남포역에서 버스 환승 필요', TRUE, '전시시설의 식품 알레르기 대응 여부는 현장에서 별도 확인', 'https://www.mmk.or.kr/', '2026-09-21'),
    (2, '부산', '영화의전당', '문화시설', '부산광역시 해운대구 수영강변대로 120', '센텀시티역 인근', TRUE, '식음 매장별 알레르기 유발 성분을 직접 확인', 'https://www.dureraum.org/', '2026-09-21'),
    (3, '부산', '해운대해수욕장', '해변', '부산광역시 해운대구 해운대해변로 264', '해운대역 인근', FALSE, '주변 음식점의 알레르기 대응 여부는 매장별 확인', 'https://www.visitbusan.net/', '2026-09-21')
ON CONFLICT (place_id) DO UPDATE SET city=EXCLUDED.city, name=EXCLUDED.name, category=EXCLUDED.category, address=EXCLUDED.address, nearest_station=EXCLUDED.nearest_station, indoor=EXCLUDED.indoor, allergy_note=EXCLUDED.allergy_note, source_url=EXCLUDED.source_url, verified_at=EXCLUDED.verified_at;

INSERT INTO mini_multi_agent_01.transit_guides VALUES
    (1, '부산', '부산역', '영화의전당', '도시철도', '1호선 이용 후 서면역에서 2호선으로 환승하여 센텀시티역 하차', NULL, NULL, 'https://www.humetro.busan.kr/', '2026-09-21'),
    (2, '부산', '부산역', '해운대해수욕장', '도시철도', '1호선 이용 후 서면역에서 2호선으로 환승하여 해운대역 하차', NULL, NULL, 'https://www.humetro.busan.kr/', '2026-09-21'),
    (3, '부산', '부산역', '국립해양박물관', '도시철도+버스', '남포역 이동 후 영도 방면 시내버스로 환승; 정확한 도착 정보는 당일 교통 앱 확인', NULL, NULL, 'https://www.busan.go.kr/bhbustrans/index', '2026-09-21')
ON CONFLICT (guide_id) DO UPDATE SET city=EXCLUDED.city, origin=EXCLUDED.origin, destination=EXCLUDED.destination, transport_type=EXCLUDED.transport_type, route_summary=EXCLUDED.route_summary, estimated_minutes=EXCLUDED.estimated_minutes, estimated_fare=EXCLUDED.estimated_fare, source_url=EXCLUDED.source_url, verified_at=EXCLUDED.verified_at;

INSERT INTO mini_multi_agent_01.allergy_guidance VALUES
    (1, '공통', '식품 알레르기 확인', '주문 전에 알레르기 유발 식품과 교차접촉 가능성을 매장에 직접 확인하고, 확인되지 않으면 섭취하지 않습니다.', FALSE, 'https://www.foodsafetykorea.go.kr/', '2026-09-21'),
    (2, '공통', '응급 대응', '호흡곤란 등 중증 증상이 의심되면 즉시 119에 신고하고 개인 처방 응급약이 있다면 의료진 지시에 따릅니다.', TRUE, 'https://www.119.go.kr/', '2026-09-21'),
    (3, '부산', '방문 전 확인', '여행 일정의 식당은 알레르기 대응 인증 장소로 간주하지 않으며 방문 전에 식재료와 조리 환경을 확인합니다.', FALSE, 'https://www.visitbusan.net/', '2026-09-21')
ON CONFLICT (guidance_id) DO UPDATE SET city=EXCLUDED.city, title=EXCLUDED.title, guidance=EXCLUDED.guidance, emergency=EXCLUDED.emergency, source_url=EXCLUDED.source_url, verified_at=EXCLUDED.verified_at;

INSERT INTO mini_multi_agent_01.content_facts VALUES
    (1, '부산', '부산은 대한민국의 광역시이다.', 'https://www.busan.go.kr/', '2026-09-21'),
    (2, '부산', '부산도시철도는 부산교통공사가 운영 정보를 제공한다.', 'https://www.humetro.busan.kr/', '2026-09-21'),
    (3, '부산', '부산 공식 관광 정보는 Visit Busan에서 확인할 수 있다.', 'https://www.visitbusan.net/', '2026-09-21')
ON CONFLICT (fact_id) DO UPDATE SET topic=EXCLUDED.topic, fact=EXCLUDED.fact, source_url=EXCLUDED.source_url, verified_at=EXCLUDED.verified_at;

INSERT INTO mini_multi_agent_01.quality_requirements VALUES
    (1, 'content', 'source_confirmation', '출처 확인 문구를 포함한다.', 'internal://course/content-contract', '2026-09-21'),
    (2, 'content', 'user_approval', '사용자 승인 문구를 포함한다.', 'internal://course/content-contract', '2026-09-21'),
    (3, 'code', 'validation_boundary', '사용자 입력 검증은 시스템 경계에서 수행한다.', 'internal://course/code-contract', '2026-09-21'),
    (4, 'code', 'error_contract', '검증 실패의 오류 형식과 상태를 정의한다.', 'internal://course/code-contract', '2026-09-21'),
    (5, 'code', 'tests', '정상·경계·실패 입력 테스트를 포함한다.', 'internal://course/code-contract', '2026-09-21')
ON CONFLICT (requirement_id) DO UPDATE SET scenario=EXCLUDED.scenario, requirement_key=EXCLUDED.requirement_key, requirement_text=EXCLUDED.requirement_text, source_url=EXCLUDED.source_url, verified_at=EXCLUDED.verified_at;

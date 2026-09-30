CREATE SCHEMA IF NOT EXISTS mini_multi_agent_03;
CREATE TABLE IF NOT EXISTS mini_multi_agent_03.orders(order_id TEXT PRIMARY KEY,status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mini_multi_agent_03.refund_policies(policy_id INTEGER PRIMARY KEY,policy_text TEXT NOT NULL,active BOOLEAN NOT NULL);
CREATE TABLE IF NOT EXISTS mini_multi_agent_03.help_articles(topic TEXT PRIMARY KEY,article TEXT NOT NULL);
INSERT INTO mini_multi_agent_03.orders VALUES('ORDER-102','배송 지연') ON CONFLICT(order_id) DO UPDATE SET status=EXCLUDED.status;
INSERT INTO mini_multi_agent_03.refund_policies VALUES(1,'배송 지연 주문은 상태 확인 후 환불 정책을 안내합니다. 실제 환불은 실행하지 않습니다.',TRUE) ON CONFLICT(policy_id) DO UPDATE SET policy_text=EXCLUDED.policy_text;
INSERT INTO mini_multi_agent_03.help_articles VALUES('로그인','비밀번호 재설정과 계정 잠금 상태를 확인하세요.') ON CONFLICT(topic) DO UPDATE SET article=EXCLUDED.article;

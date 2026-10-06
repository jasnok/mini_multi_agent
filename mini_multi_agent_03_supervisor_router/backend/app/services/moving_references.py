"""고정된 공식 안내 주소만 읽기 전용 조회. 사용자 주소·참고사항을 전송하지 않는다."""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

SOURCES = {
    "gwanak_waste": {"title": "관악구 대형폐기물 공식 안내", "url": "https://smartclean.gwanak.go.kr/", "item_ids": ["waste_booking", "waste"], "description": "대상·수수료·배출 방법은 공식 페이지에서 확인하세요."},
    "gangbuk": {"title": "강북구청 생활 민원 안내", "url": "https://www.gangbuk.go.kr/", "item_ids": ["waste_booking", "waste"], "description": "홈페이지의 대형폐기물 메뉴에서 해당 지역 안내를 확인하세요."},
    "address": {"title": "정부24 전입신고 안내", "url": "https://www.gov.kr/mw/AA020InfoCappView.do?CappBizCD=13100000016", "item_ids": ["address"], "description": "신청 자격·준비 사항은 공식 안내에서 확인하세요. 이 사이트는 신고를 수행하지 않습니다."},
}


def reference_catalog(origin, destination):
    keys = ["address"]
    if "관악" in origin or "관악" in destination: keys.append("gwanak_waste")
    if "강북" in origin or "수유" in origin or "강북" in destination or "수유" in destination: keys.append("gangbuk")
    return [{"source_id": key, **SOURCES[key], "checked_at": None, "status": "not_checked"} for key in keys]


async def check_references(source_ids):
    if set(source_ids) - SOURCES.keys():
        raise ValueError("허용되지 않은 공식 안내 출처입니다.")
    async def check(key):
        source = SOURCES[key]
        result = {"source_id": key, **source, "checked_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}
        try:
            async with httpx.AsyncClient(timeout=6, follow_redirects=False) as client:
                async with client.stream("GET", source["url"]) as response:
                    result.update(status="reachable" if response.status_code == 200 else "unavailable", http_status=response.status_code)
        except httpx.HTTPError:
            result.update(status="unavailable", http_status=None)
        return result
    return await asyncio.gather(*(check(key) for key in source_ids))

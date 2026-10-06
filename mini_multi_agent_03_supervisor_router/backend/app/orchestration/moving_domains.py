"""템플릿 항목의 소유권. 모델이 담당 분야·날짜를 변경하지 않는다."""
DOMAIN_AGENTS = {
    "packing": "move_packing_agent", "disposal": "move_disposal_agent",
    "services": "move_services_agent", "housing": "move_housing_agent",
}
DOMAIN_IDS = {
    "packing": {"service_scope", "packing", "essentials", "photos", "unpack", "layout"},
    "disposal": {"sort_items", "waste_booking", "waste", "trash_bags", "fridge"},
    "services": {"internet", "utilities", "appliances", "gas", "autopay", "washer", "security"},
    "housing": {"building_access", "departure_check", "arrival_check", "address", "home_inspection",
                "school", "care", "mail", "deliveries", "final_schedule", "payment", "settlement", "resident_setup"},
}

def domain_items(template, domain):
    return [item for item in template["items"] if item["item_id"] in DOMAIN_IDS[domain]]

def required_links(notes, item_plans=()):
    links = set()
    # 같은 물품의 문맥만 검사해 다른 물품의 판매·폐기와 연결하지 않는다.
    import re
    clauses = re.split(r"[。.!?\n]|(?:하고|이고)\s*", notes["source_notes"])
    for text in clauses:
        if "가스레인지" in text and any(word in text for word in ("판매", "폐기")) and not any(word in text for word in ("판매하지", "폐기하지")):
            links.add("gas")
        if "에어컨" in text and "폐기" in text and "폐기하지" not in text:
            links.add("appliances")
    for item in item_plans:
        name, disposition = item["name"], item["disposition"]
        if "가스레인지" in name:
            links.discard("gas")
            if disposition in {"sell", "dispose"}: links.add("gas")
        if "에어컨" in name:
            links.discard("appliances")
            if disposition == "dispose": links.add("appliances")
    return sorted(links)


def enrich_template(template):
    """기존 MCP 계약을 유지하며 접수 준비와 실제 배출을 구분한다."""
    import copy
    template = copy.deepcopy(template)
    waste = next(item for item in template["items"] if item["item_id"] == "waste")
    if not any(item["item_id"] == "waste_booking" for item in template["items"]):
        template["items"].append({**waste, "item_id": "waste_booking", "title": "폐기 접수·수거 일정 미리 확인",
                                  "days_offset": -10, "guidance": "폐기할 물품이 있으면 관할 구청·수거 서비스에 대상·비용·접수·배출일을 미리 확인하세요. 철거 완료 전에도 접수 방법과 일정을 알아볼 수 있습니다."})
    waste.update(title="철거 후 판매 인계·폐기물 배출 확인", days_offset=-3,
                 guidance="판매할 물품은 구매자와 인계 담당·시간을 확인하고, 폐기할 물품은 전문 철거가 필요한지 확인한 뒤 완료 후 약정한 방식으로 배출하세요. 접수 준비와 실제 배출을 구분하세요.")
    return template

"""Сделки amoCRM без задач или с просроченными задачами (API v4)."""
import os
import time

import requests

BASE = f"https://{os.environ['AMO_SUBDOMAIN']}.amocrm.ru/api/v4"
HEADERS = {"Authorization": f"Bearer {os.environ['AMO_TOKEN']}"}
CLOSED = {142, 143}  # системные статусы «Успешно реализовано» и «Закрыто и не реализовано»


def fetch_all(path: str, params: dict, key: str) -> list[dict]:
    items, page = [], 1
    while True:
        r = requests.get(f"{BASE}/{path}", headers=HEADERS,
                         params={**params, "limit": 250, "page": page}, timeout=30)
        if r.status_code == 204:  # amoCRM отвечает 204, когда данных больше нет
            return items
        r.raise_for_status()
        data = r.json()
        items += data["_embedded"][key]
        if "next" not in data.get("_links", {}):
            return items
        page += 1
        time.sleep(0.15)  # лимит amoCRM: не больше 7 запросов в секунду


def stale_leads() -> list[dict]:
    now = int(time.time())
    leads = [l for l in fetch_all("leads", {}, "leads") if l["status_id"] not in CLOSED]
    tasks = fetch_all("tasks", {"filter[entity_type]": "leads", "filter[is_completed]": 0}, "tasks")

    nearest: dict[int, int] = {}  # id сделки -> самый ранний срок среди её незакрытых задач
    for t in tasks:
        nearest[t["entity_id"]] = min(t["complete_till"], nearest.get(t["entity_id"], t["complete_till"]))

    result = []
    for lead in leads:
        due = nearest.get(lead["id"])
        if due is None or due < now:
            result.append({"id": lead["id"], "name": lead["name"],
                           "responsible": lead["responsible_user_id"],
                           "reason": "нет задач" if due is None else "задача просрочена"})
    return result


if __name__ == "__main__":
    for row in stale_leads():
        print(row)

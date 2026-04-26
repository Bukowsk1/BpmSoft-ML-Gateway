from __future__ import annotations

from datetime import date
import json
import os

import httpx
import pandas as pd
import streamlit as st


API_URL = st.sidebar.text_input(
    "API base URL",
    value=os.getenv("BPMSOFT_DASHBOARD_API_URL", "http://127.0.0.1:8000/api"),
)

st.set_page_config(page_title="BPMSoft ДЕМО", layout="wide")
st.title("BPMSoft ДЕМО")
st.caption("Интерактивный дашборд ML сервисов")


def post_json(path: str, payload: dict) -> tuple[bool, dict]:
    try:
        response = httpx.post(f"{API_URL}{path}", json=payload, timeout=60.0)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:
        return False, {"error": str(exc)}


def get_json(path: str) -> tuple[bool, dict]:
    try:
        response = httpx.get(f"{API_URL}{path}", timeout=30.0)
        response.raise_for_status()
        return True, response.json()
    except Exception as exc:
        return False, {"error": str(exc)}


if "demand_payload" not in st.session_state:
    st.session_state.demand_payload = {
        "records": [
            {
                "date": "2025-01-07",
                "sku": "MI-006",
                "brand": "MiBrand1",
                "segment": "Milk-Seg3",
                "category": "Milk",
                "channel": "Retail",
                "region": "PL-Central",
                "pack_type": "Multipack",
                "price_unit": 2.38,
                "promotion_flag": 0,
                "delivery_days": 1,
                "stock_available": 141,
                "delivered_qty": 128,
                "units_sold": 0,
            }
        ]
    }

if "price_payload" not in st.session_state:
    st.session_state.price_payload = {
        "sku": "MI-006",
        "brand": "MiBrand1",
        "category": "Milk",
        "region": "PL-Central",
        "current_price": 2.38,
        "stock_available": 141,
        "delivered_qty": 128,
        "promotion_flag": 0,
    }

if "demand_result" not in st.session_state:
    st.session_state.demand_result = None

if "price_result" not in st.session_state:
    st.session_state.price_result = None


with st.expander("Healthcheck", expanded=True):
    if st.button("Обновить статус API", use_container_width=True):
        st.rerun()
    try:
        health_response = httpx.get(f"{API_URL}/health", timeout=10.0)
        st.json(health_response.json())
    except Exception as exc:
        st.warning(f"API пока недоступен: {exc}")


left, right = st.columns(2)

with left:
    st.subheader("Прогноз спроса")
    sample_left, _ = st.columns(2)
    if sample_left.button("Пример запроса (Спрос)", use_container_width=True):
        ok, result = get_json("/predict/demand/sample")
        if ok:
            st.session_state.demand_payload = result
            st.rerun()
        st.error(result["error"]) if not ok else None

    with st.expander("Редактировать входные данные напрямую"):
        demand_payload_text = st.text_area(
            "Demand payload",
            value=json.dumps(st.session_state.demand_payload, ensure_ascii=False, indent=2),
            height=260,
        )
        if st.button("Применить JSON payload", use_container_width=True):
            try:
                st.session_state.demand_payload = json.loads(demand_payload_text)
                st.rerun()
            except json.JSONDecodeError as exc:
                st.error(f"Некорректный JSON: {exc}")

    with st.form("demand-form"):
        current_record = st.session_state.demand_payload["records"][0]
        forecast_date = st.date_input("Date", value=date.fromisoformat(current_record["date"]))
        sku = st.text_input("SKU", value=current_record["sku"])
        brand = st.text_input("Brand", value=current_record["brand"])
        segment = st.text_input("Segment", value=current_record["segment"])
        category = st.text_input("Category", value=current_record["category"])
        channel = st.text_input("Channel", value=current_record["channel"])
        region = st.text_input("Region", value=current_record["region"])
        pack_type = st.text_input("Pack type", value=current_record["pack_type"])
        price_unit = st.number_input("Price unit", min_value=0.0, value=float(current_record["price_unit"]), step=0.01)
        promotion_flag = st.selectbox("Promotion flag", options=[0, 1], index=int(current_record["promotion_flag"]))
        delivery_days = st.number_input("Delivery days", min_value=0, value=int(current_record["delivery_days"]), step=1)
        stock_available = st.number_input("Stock available", min_value=0, value=int(current_record["stock_available"]), step=1)
        delivered_qty = st.number_input("Delivered qty", min_value=0, value=int(current_record["delivered_qty"]), step=1)
        units_sold = st.number_input("Units sold", min_value=0, value=int(current_record["units_sold"]), step=1)
        submit_demand = st.form_submit_button("Отправить в модель", use_container_width=True)

    if submit_demand:
        records = st.session_state.demand_payload.get("records", [])
        updated_first_record = {
            "date": forecast_date.isoformat(),
            "sku": sku,
            "brand": brand,
            "segment": segment,
            "category": category,
            "channel": channel,
            "region": region,
            "pack_type": pack_type,
            "price_unit": price_unit,
            "promotion_flag": promotion_flag,
            "delivery_days": delivery_days,
            "stock_available": stock_available,
            "delivered_qty": delivered_qty,
            "units_sold": units_sold,
        }
        st.session_state.demand_payload = {"records": [updated_first_record, *records[1:]]}
        ok, result = post_json("/predict/demand", st.session_state.demand_payload)
        if ok:
            st.success("Запрос выполнен.")
        else:
            st.error("Запрос завершился ошибкой.")
        if ok:
            st.session_state.demand_result = result
        st.json(result)

    if st.session_state.demand_result:
        result_df = pd.DataFrame(st.session_state.demand_result["items"])
        st.dataframe(result_df, use_container_width=True)
        st.download_button(
            "Скачать прогноз",
            data=result_df.to_csv(index=False).encode("utf-8"),
            file_name="demand_predictions.csv",
            mime="text/csv",
            use_container_width=True,
        )

with right:
    st.subheader("Прогноз цены (заглушка)")
    sample_right, _ = st.columns(2)
    if sample_right.button("Пример запроса (Цена)", use_container_width=True):
        ok, result = get_json("/predict/price/sample")
        if ok:
            st.session_state.price_payload = result
            st.rerun()
        st.error(result["error"]) if not ok else None

    with st.form("price-form"):
        current_price_payload = st.session_state.price_payload
        price_sku = st.text_input("SKU ", value=current_price_payload["sku"])
        price_brand = st.text_input("Brand ", value=current_price_payload["brand"])
        price_category = st.text_input("Category ", value=current_price_payload["category"])
        price_region = st.text_input("Region ", value=current_price_payload["region"])
        current_price = st.number_input("Current price", min_value=0.0, value=float(current_price_payload["current_price"]), step=0.01)
        price_stock_available = st.number_input("Stock available ", min_value=0, value=int(current_price_payload["stock_available"]), step=1)
        price_delivered_qty = st.number_input("Delivered qty ", min_value=0, value=int(current_price_payload["delivered_qty"]), step=1)
        price_promo = st.selectbox("Promotion flag ", options=[0, 1], index=int(current_price_payload["promotion_flag"]))
        submit_price = st.form_submit_button("Отправить в модель", use_container_width=True)

    if submit_price:
        st.session_state.price_payload = {
            "sku": price_sku,
            "brand": price_brand,
            "category": price_category,
            "region": price_region,
            "current_price": current_price,
            "stock_available": price_stock_available,
            "delivered_qty": price_delivered_qty,
            "promotion_flag": price_promo,
        }
        ok, result = post_json("/predict/price", st.session_state.price_payload)
        if ok:
            st.success("Запрос выполнен.")
        else:
            st.error("Запрос завершился ошибкой.")
        if ok:
            st.session_state.price_result = result
        st.json(result)

    if st.session_state.price_result:
        st.metric(
            "Рекомендованная цена",
            f'{st.session_state.price_result["recommended_price"]} {st.session_state.price_result["currency"]}',
        )
        st.caption(st.session_state.price_result["reasoning"])

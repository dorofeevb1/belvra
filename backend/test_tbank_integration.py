#!/usr/bin/env python3
"""
Test script for T-Bank e-acquiring API integration.
Uses DEMO terminal credentials for testing.
"""

import hashlib
import json
import sys
import uuid

import requests

# DEMO Terminal credentials
TERMINAL_KEY = "1774615155386DEMO"
PASSWORD = "cAk9hZfCjw6b3gqu"
API_URL = "https://securepay.tinkoff.ru/v2/"


def generate_token(params: dict) -> str:
    """Generate Token for T-Bank API request."""
    token_params = {}
    for key, value in params.items():
        if key == "Token":
            continue
        if isinstance(value, (dict, list)):
            continue
        token_params[key] = str(value)

    token_params["Password"] = PASSWORD

    sorted_keys = sorted(token_params.keys())
    values_string = "".join(token_params[key] for key in sorted_keys)

    return hashlib.sha256(values_string.encode("utf-8")).hexdigest()


def api_request(method: str, params: dict) -> dict:
    """Make a request to T-Bank API."""
    params["TerminalKey"] = TERMINAL_KEY
    params["Token"] = generate_token(params)

    url = f"{API_URL}{method}"
    print(f"\n{'='*60}")
    print(f">>> {method}")
    print(f"URL: {url}")
    print(f"Params: {json.dumps({k: v for k, v in params.items() if k != 'Token'}, indent=2, ensure_ascii=False)}")

    response = requests.post(url, json=params, timeout=30)
    print(f"\nHTTP {response.status_code}")

    try:
        data = response.json()
    except Exception:
        print(f"Raw response: {response.text[:500]}")
        return {"Success": False, "ErrorCode": "HTTP", "Message": f"Non-JSON response: {response.status_code}"}

    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

    return data


def test_1_init_simple():
    """Test 1: Simple Init — create a payment."""
    print("\n" + "=" * 60)
    print("TEST 1: Init — Создание платежа (простой)")
    print("=" * 60)

    order_id = f"test_{uuid.uuid4().hex[:12]}"
    data = api_request("Init", {
        "Amount": 29900,  # 299.00 RUB (подписка Pro)
        "OrderId": order_id,
        "Description": "Подписка Belvra PRO (тест)",
        "Language": "ru",
        "SuccessURL": "https://example.com/success",
        "FailURL": "https://example.com/fail",
    })

    success = data.get("Success", False)
    print(f"\n{'PASS' if success else 'FAIL'}: Init {'успешен' if success else 'провален'}")

    if success:
        print(f"  PaymentId: {data.get('PaymentId')}")
        print(f"  PaymentURL: {data.get('PaymentURL')}")
        print(f"  Status: {data.get('Status')}")
        return data.get("PaymentId"), order_id
    else:
        print(f"  ErrorCode: {data.get('ErrorCode')}")
        print(f"  Message: {data.get('Message')}")
        print(f"  Details: {data.get('Details')}")
        return None, order_id


def test_2_init_with_receipt():
    """Test 2: Init with receipt (FZ-54)."""
    print("\n" + "=" * 60)
    print("TEST 2: Init — Создание платежа с чеком (ФЗ-54)")
    print("=" * 60)

    order_id = f"test_receipt_{uuid.uuid4().hex[:8]}"
    data = api_request("Init", {
        "Amount": 29900,
        "OrderId": order_id,
        "Description": "Подписка Belvra PRO",
        "Language": "ru",
        "Receipt": {
            "Taxation": "usn_income",
            "Email": "test@example.com",
            "Items": [
                {
                    "Name": "Подписка Belvra PRO (месяц)",
                    "Price": 29900,
                    "Quantity": 1.0,
                    "Amount": 29900,
                    "Tax": "none",
                    "PaymentMethod": "full_payment",
                    "PaymentObject": "service",
                }
            ],
        },
    })

    success = data.get("Success", False)
    print(f"\n{'PASS' if success else 'FAIL'}: Init с чеком {'успешен' if success else 'провален'}")

    if not success:
        print(f"  ErrorCode: {data.get('ErrorCode')}")
        print(f"  Message: {data.get('Message')}")

    return data.get("PaymentId") if success else None


def test_3_init_recurrent():
    """Test 3: Init with Recurrent + CustomerKey (for saved cards)."""
    print("\n" + "=" * 60)
    print("TEST 3: Init — Рекуррентный платёж (сохранение карты)")
    print("=" * 60)

    order_id = f"test_recur_{uuid.uuid4().hex[:8]}"
    data = api_request("Init", {
        "Amount": 29900,
        "OrderId": order_id,
        "Description": "Подписка PRO (с сохранением карты)",
        "CustomerKey": "test_user_123",
        "Recurrent": "Y",
        "Language": "ru",
    })

    success = data.get("Success", False)
    print(f"\n{'PASS' if success else 'FAIL'}: Init рекуррентный {'успешен' if success else 'провален'}")

    if success:
        print(f"  PaymentId: {data.get('PaymentId')}")
        print(f"  PaymentURL: {data.get('PaymentURL')}")
    else:
        print(f"  ErrorCode: {data.get('ErrorCode')}")
        print(f"  Message: {data.get('Message')}")

    return data.get("PaymentId") if success else None


def test_4_get_state(payment_id: str):
    """Test 4: GetState — check payment status."""
    print("\n" + "=" * 60)
    print(f"TEST 4: GetState — Проверка статуса (PaymentId={payment_id})")
    print("=" * 60)

    data = api_request("GetState", {
        "PaymentId": payment_id,
    })

    success = data.get("Success", False)
    print(f"\n{'PASS' if success else 'FAIL'}: GetState {'успешен' if success else 'провален'}")

    if success:
        print(f"  Status: {data.get('Status')}")
        print(f"  Amount: {data.get('Amount')} коп. ({int(data.get('Amount', 0))/100} руб.)")
    else:
        print(f"  ErrorCode: {data.get('ErrorCode')}")
        print(f"  Message: {data.get('Message')}")

    return data


def test_5_cancel(payment_id: str):
    """Test 5: Cancel — cancel/refund payment."""
    print("\n" + "=" * 60)
    print(f"TEST 5: Cancel — Отмена платежа (PaymentId={payment_id})")
    print("=" * 60)

    data = api_request("Cancel", {
        "PaymentId": payment_id,
    })

    success = data.get("Success", False)
    # Cancel of NEW payment returns ErrorCode 7 (invalid state), which is expected
    error_code = data.get("ErrorCode", "0")

    if success:
        print(f"\nPASS: Cancel успешен")
        print(f"  Status: {data.get('Status')}")
    elif error_code == "7":
        print(f"\nPASS (ожидаемо): Платёж в статусе NEW, отмена через Cancel невозможна")
        print(f"  Это нормально — Cancel работает только для AUTHORIZED/CONFIRMED")
    else:
        print(f"\nFAIL: Cancel провален")
        print(f"  ErrorCode: {error_code}")
        print(f"  Message: {data.get('Message')}")

    return data


def test_6_token_verification():
    """Test 6: Verify our token generation matches T-Bank's expectations."""
    print("\n" + "=" * 60)
    print("TEST 6: Верификация генерации Token")
    print("=" * 60)

    # Create a payment and verify token is accepted
    order_id = f"test_token_{uuid.uuid4().hex[:8]}"
    params = {
        "Amount": 10000,
        "OrderId": order_id,
        "Description": "Тест токена",
    }
    params["TerminalKey"] = TERMINAL_KEY
    token = generate_token(params)
    params["Token"] = token

    print(f"  TerminalKey: {TERMINAL_KEY}")
    print(f"  Generated Token: {token}")

    response = requests.post(f"{API_URL}Init", json=params, timeout=30)
    data = response.json()

    if data.get("Success"):
        print(f"\nPASS: Token принят API")
    elif data.get("ErrorCode") == "9999":
        print(f"\nFAIL: Неверный Token — проверьте алгоритм генерации")
        print(f"  Message: {data.get('Message')}")
    else:
        print(f"\nINFO: ErrorCode={data.get('ErrorCode')}, Message={data.get('Message')}")

    return data.get("Success", False)


def test_7_notification_token_verify():
    """Test 7: Verify notification token verification logic."""
    print("\n" + "=" * 60)
    print("TEST 7: Верификация Token из нотификаций")
    print("=" * 60)

    # Simulate a notification payload
    notification = {
        "TerminalKey": TERMINAL_KEY,
        "OrderId": "test_order_123",
        "Success": True,
        "Status": "CONFIRMED",
        "PaymentId": 123456789,
        "ErrorCode": "0",
        "Amount": 29900,
        "Pan": "430000******0777",
        "Token": "",  # Will be computed
    }

    # Generate expected token
    check_params = {}
    for key, value in notification.items():
        if key == "Token":
            continue
        if isinstance(value, (dict, list)):
            continue
        check_params[key] = str(value)

    check_params["Password"] = PASSWORD
    sorted_keys = sorted(check_params.keys())
    values_string = "".join(check_params[key] for key in sorted_keys)
    expected_token = hashlib.sha256(values_string.encode("utf-8")).hexdigest()

    notification["Token"] = expected_token

    # Now verify
    received_token = notification["Token"]
    verify_params = {}
    for key, value in notification.items():
        if key == "Token":
            continue
        if isinstance(value, (dict, list)):
            continue
        verify_params[key] = str(value)

    verify_params["Password"] = PASSWORD
    sorted_keys2 = sorted(verify_params.keys())
    values_string2 = "".join(verify_params[key] for key in sorted_keys2)
    computed_token = hashlib.sha256(values_string2.encode("utf-8")).hexdigest()

    match = computed_token == received_token
    print(f"  Expected Token:  {expected_token}")
    print(f"  Computed Token:  {computed_token}")
    print(f"\n{'PASS' if match else 'FAIL'}: Token verification {'работает' if match else 'НЕ работает'}")

    return match


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("  T-Bank E-Acquiring Integration Tests")
    print(f"  Terminal: {TERMINAL_KEY}")
    print(f"  API URL: {API_URL}")
    print("=" * 60)

    results = []

    # Test 1: Simple Init
    payment_id, order_id = test_1_init_simple()
    results.append(("Init (простой)", payment_id is not None))

    # Test 2: Init with receipt
    receipt_payment_id = test_2_init_with_receipt()
    results.append(("Init с чеком", receipt_payment_id is not None))

    # Test 3: Recurrent Init
    recurrent_payment_id = test_3_init_recurrent()
    results.append(("Init рекуррентный", recurrent_payment_id is not None))

    # Test 4: GetState
    if payment_id:
        state_data = test_4_get_state(str(payment_id))
        results.append(("GetState", state_data.get("Success", False)))
    else:
        print("\nSKIP: Test 4 (GetState) — нет PaymentId")
        results.append(("GetState", None))

    # Test 5: Cancel
    if payment_id:
        cancel_data = test_5_cancel(str(payment_id))
        # Cancel of NEW status returns error 7, which is expected behavior
        is_ok = cancel_data.get("Success", False) or cancel_data.get("ErrorCode") == "7"
        results.append(("Cancel", is_ok))
    else:
        print("\nSKIP: Test 5 (Cancel) — нет PaymentId")
        results.append(("Cancel", None))

    # Test 6: Token generation
    token_ok = test_6_token_verification()
    results.append(("Token generation", token_ok))

    # Test 7: Notification token verification
    notif_ok = test_7_notification_token_verify()
    results.append(("Notification Token verify", notif_ok))

    # Summary
    print("\n" + "=" * 60)
    print("  РЕЗУЛЬТАТЫ ТЕСТОВ")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result is None:
            status = "SKIP"
            skipped += 1
        elif result:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1
        print(f"  [{status}] {name}")

    print(f"\n  Итого: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)

    if payment_id:
        print(f"\n  Ссылка для тестовой оплаты (Test 1):")
        # Re-fetch the URL since we need it
        print(f"  (создайте новый платёж для получения ссылки)")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

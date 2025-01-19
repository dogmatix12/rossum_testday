from src.main import parse_document


def test_normalize_document(sample_annotation_payload):
    parsed_document = parse_document(payload=sample_annotation_payload)
    payable = parsed_document["InvoiceRegisters"]["Invoices"]["Payable"]

    assert payable["Notes"] is None
    assert "143453775" == payable["InvoiceNumber"]

    assert payable["Details"][1]["Detail"]["Amount"] == "2077.14"
    assert 3 == len(payable["Details"])

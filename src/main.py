import base64
import logging
from datetime import datetime

import requests
from dict2xml import DataSorter, dict2xml
from typing_extensions import Buffer

from src.config import Config

config = Config()
logging.getLogger().addHandler(logging.StreamHandler())

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _response_handler(response: requests.Response) -> dict:
    response.raise_for_status()

    logger.debug(f"Response: {response.status_code}, {response.text}")
    return (
        response.json()
        if "application/json" in response.headers.get("Content-Type", "")
        else {"text": response.text}
    )


def _convert_to_base64(xml_data: Buffer) -> str:
    return base64.b64encode(xml_data).decode(config.xml_encoding or "utf-8")


def _normalize_datapoint_value(datapoint: dict) -> str:
    if not (value := datapoint.get("value")):
        return ""

    if datapoint.get("type") == "date":
        date_obj = datetime.strptime(value, "%Y-%m-%d")
        return date_obj.strftime("%Y-%m-%dT%H:%M:%S")

    if datapoint.get("type") == "enum":
        return value.upper()

    return datapoint["value"]


def _normalize_multivalue(children: dict) -> dict:
    return children


def obtain_annotations(document_id: str) -> dict:
    return _response_handler(
        config.http_session.post(
            f"{config.rossum_base_url}/api/v1/annotations/export",
            headers={
                "Authorization": f"Bearer {config.rossum_auth_token}",
                "Content-Type": "application/json",
            },
            params={
                "format": "json",
            },
            json={"annotations": [f"{config.rossum_base_url}/api/v1/annotations/{document_id}"]},
        )
    )


def make_invoices_xml(rossum_doc: dict) -> str:
    xml_declaration = f'<?xml version="1.0" encoding="{config.xml_encoding}"?>\n'

    return xml_declaration + dict2xml(
        data=rossum_doc,
        closed_tags_for=[None],
        iterables_repeat_wrap=False,
        data_sorter=DataSorter.never(),
    )


def upload_result(annotation_id: str, xml_data: str):
    xml_data_base64 = _convert_to_base64(xml_data.encode())

    logger.info(f"Uploading XML Data to Rossum: {annotation_id}, {xml_data_base64}")

    return _response_handler(
        config.http_session.post(
            f"{config.target_endpoint}",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "annotationId": annotation_id,
                "content": xml_data_base64,
            },
        )
    )


def _obtain_section(content, schema_id: str) -> dict:
    for section in content:
        if section.get("schema_id") == schema_id:
            if section.get("category") in ["section", "tuple"]:
                logger.debug(f"Found section: {schema_id}")

                mapped_datapoints = {
                    child["schema_id"]: _normalize_datapoint_value(child)
                    for child in section["children"]
                    if "value" in child and child.get("category") == "datapoint"
                } | {
                    child["schema_id"]: _normalize_multivalue(child)
                    for child in section["children"]
                    if "children" in child and child.get("category") == "multivalue"
                }

                return mapped_datapoints

            if section.get("category") == "multivalue":
                return section.get("children")

    return {}


def parse_document(payload: dict) -> dict:
    content = payload["results"][0]["content"]

    basic_info_section = _obtain_section(content=content, schema_id="basic_info_section")
    payment_info_section = _obtain_section(content=content, schema_id="payment_info_section")
    amounts_section = _obtain_section(content=content, schema_id="amounts_section")
    vendor_section = _obtain_section(content=content, schema_id="vendor_section")
    other_section = _obtain_section(content=content, schema_id="other_section")
    line_items_section = _obtain_section(content=content, schema_id="line_items_section")
    line_items = line_items_section.get("line_items", {}).get("children", [])

    def make_detail(line_item):
        line_item_dict = _obtain_section(content=[line_item], schema_id="line_item")
        return {
            "Detail": {
                "Amount": line_item_dict.get("item_amount"),
                "AccountId": line_item_dict.get("account_id"),
                "Quantity": line_item_dict.get("item_quantity"),
                "Notes": line_item_dict.get("item_description"),
            }
        }

    return {
        "InvoiceRegisters": {
            "Invoices": {
                "Payable": {
                    "InvoiceNumber": basic_info_section.get("document_id"),
                    "InvoiceDate": basic_info_section.get("date_issue"),  # "2019-03-01T00:00:00"
                    "DueDate": basic_info_section.get("date_due"),  # "2019-03-31T00:00:00"
                    "TotalAmount": amounts_section.get("amount_total"),  # "2706.00"
                    "Notes": other_section.get("notes") or None,  # <Notes/>
                    "Iban": payment_info_section.get("iban"),  # NO6513425245230
                    "Amount": line_items_section.get("item_amount_total"),  # 2595.76
                    "Currency": amounts_section.get("currency"),  # "NOK",
                    "Vendor": vendor_section.get("recipient_name"),  # "InfoNet Workshop",
                    "VendorAddress": vendor_section.get(
                        "recipient_address"
                    ),  # "2423 KONGSVINGER Norway",
                    "Details": [make_detail(line_item) for line_item in line_items],
                },
            }
        }
    }


if __name__ == "__main__":  # This will run if the file is run directly
    document_id = config.document_id

    assert document_id, "Document ID is required"
    logger.info(f"Parse Document ID: {document_id}")

    payload = obtain_annotations(document_id=document_id)
    logger.debug(f"Payload: {payload}")

    parsed_document = parse_document(payload=payload)
    logger.debug(f"Parsed Document: {parsed_document}")

    xml_data = make_invoices_xml(rossum_doc=parsed_document)
    logger.info(f"XML Data: {xml_data}")

    upload_result(annotation_id=document_id, xml_data=xml_data)

    logger.info("Done")

"""
This custom serverless function example demonstrates showing messages to the
user on the validation screen, updating values of specific fields, and
executing actions on the annotation.

See https://elis.rossum.ai/api/docs/#rossum-transaction-scripts for more examples.

Document ID: 6394865
"""

import base64
import json
import urllib.request
import xml.etree.cElementTree as ET
from functools import reduce
from operator import add

from txscript import TxScript, is_empty
from txscript.datapoint import DateValue, FieldValueBase
from typing_extensions import Buffer

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def _format_value(field: FieldValueBase) -> str | None:
    if is_empty(field):
        return None

    if isinstance(field, DateValue):
        return field.strftime(DATE_FORMAT)

    return str(field)


def _convert_to_base64(xml_data: Buffer) -> str:
    return base64.b64encode(xml_data).decode("utf-8")


def make_detail_item(line_item):
    detail = ET.Element("Detail")

    ET.SubElement(detail, "Notes").text = _format_value(line_item.item_description)
    ET.SubElement(detail, "Amount").text = _format_value(line_item.item_amount)
    ET.SubElement(detail, "AccountId")
    ET.SubElement(detail, "Quantity").text = _format_value(line_item.item_quantity)

    return detail


def make_invoice_xml(t: TxScript):
    invoice_registers = ET.Element("InvoiceRegisters")
    invoices = ET.SubElement(invoice_registers, "Invoices")
    payable = ET.SubElement(invoices, "Payable")

    ET.SubElement(payable, "InvoiceNumber").text = _format_value(t.field.document_id)
    ET.SubElement(payable, "InvoiceDate").text = _format_value(t.field.date_issue)
    ET.SubElement(payable, "DueDate").text = _format_value(t.field.date_due)
    ET.SubElement(payable, "TotalAmount").text = _format_value(t.field.amount_total)
    ET.SubElement(payable, "Notes")
    ET.SubElement(payable, "Iban").text = _format_value(t.field.iban)

    # sum All items
    ET.SubElement(payable, "Amount").text = str(reduce(add, t.field.item_amount_total.all_values))

    ET.SubElement(payable, "Currency").text = _format_value(t.field.currency)
    ET.SubElement(payable, "Vendor").text = _format_value(t.field.recipient_name)
    ET.SubElement(payable, "VendorAddress").text = _format_value(t.field.recipient_name)

    details = ET.SubElement(payable, "Details")
    details.extend([make_detail_item(line_item) for line_item in t.field.line_items])

    return invoice_registers


def rossum_hook_request_handler(payload: dict) -> dict:
    t = TxScript.from_payload(payload)

    annotation_id = payload["annotation"]["id"]

    invoice_registers = make_invoice_xml(t)
    xml_data = ET.tostring(invoice_registers, encoding="utf-8", xml_declaration=True)
    xml_data_base64 = _convert_to_base64(xml_data)

    # print(xml_data_base64)

    json_data = json.dumps(
        {
            "annotationId": annotation_id,
            "content": xml_data_base64,
        },
        indent=4,
    )

    request = urllib.request.Request(
        "https://www.postb.in/1737911855150-6249177099671",
        headers={
            "Content-Type": "application/json",
        },
        data=json_data.encode("utf-8"),
    )
    with urllib.request.urlopen(request) as response:
        if not response.ok:
            show_warning("Cannot upload XML", str(response))

    return t.hook_response()

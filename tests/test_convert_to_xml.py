import pytest

from src.main import make_invoices_xml
from tests.conftest import load_file_content


@pytest.mark.parametrize(
    "input_dict,expected_xml",
    [
        (
            load_file_content("make_invoices_xml_input.json"),
            load_file_content("make_invoices_xml_output.xml"),
        ),
        (
            {},
            '<?xml version="1.0" encoding="utf-8"?>\n',
        ),
        (
            {"empty": None},
            '<?xml version="1.0" encoding="utf-8"?>\n<empty/>',
        ),
    ],
)
def test_make_invoices_xml(input_dict: dict, expected_xml: str):
    assert expected_xml == make_invoices_xml(input_dict)

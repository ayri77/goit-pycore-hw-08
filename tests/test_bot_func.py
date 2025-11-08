import pytest
from datetime import datetime, timedelta

from src.bot import (
    AddressBook, Record,
    add_contact, change_contact, delete_contact, delete_all,
    show_phone, show_all_cmd,
    add_birthday, show_birthday, birthdays,
    parse_input, process_line,
    MSG_ADDED, MSG_ENTER_NAME_PHONE, MSG_UPDATED, MSG_NOT_FOUND,
    MSG_DELETED, MSG_DELETED_ALL, MSG_HELLO, MSG_GOODBYE, MSG_HELP
)

import pickle
from pathlib import Path
from src.bot import AddressBook, Record

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def make_book(initial: dict[str, dict] | None = None) -> AddressBook:
    """
    initial = {
        "John": {"phones": ["0123456789","1111111111"], "birthday": "05.11.2000"},
        ...
    }
    """
    book = AddressBook()
    if not initial:
        return book
    for name, payload in initial.items():
        rec = Record(name)
        for ph in payload.get("phones", []):
            rec.add_phone(ph)
        if payload.get("birthday"):
            rec.add_birthday(payload["birthday"])
        book.add_record(rec)
    return book

# -----------------------------------------------------------------------------
# Pickle tests
# -----------------------------------------------------------------------------
def test_pickle_roundtrip(tmp_path):
    path = tmp_path / "addressbook.pkl"

    # prepare book
    book = AddressBook()
    rec = Record("John")
    rec.add_phone("0123456789")
    book.add_record(rec)

    # save
    book.save_pickle(path)

    # load
    loaded = AddressBook.load_pickle(path)

    assert isinstance(loaded, AddressBook)
    assert list(loaded.data.keys()) == ["John"]
    phones = [p.value for p in loaded.find("John").get_phones()]
    assert phones == ["0123456789"]

# -----------------------------------------------------------------------------
# add_contact
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args, expected_name, expected_phones",
    [
        (["John", "0123456789"], "John", ["0123456789"]),
        (["john doe", "1111111111"], "John Doe", ["1111111111"]),
    ],
    ids=["simple","title_case_normalization"]
)
def test_add_contact_ok(args, expected_name, expected_phones):
    book = make_book()
    msg = add_contact(args, book)
    assert msg == MSG_ADDED
    rec = book.find(expected_name)
    assert rec is not None
    assert [p.value for p in rec.get_phones()] == expected_phones

@pytest.mark.parametrize(
    "args, expected_substr",
    [
        (["John"], MSG_ENTER_NAME_PHONE),            # no phone
        ([], MSG_ENTER_NAME_PHONE),                  # no args
        (["John", "123-abc-456"], "Phone must have"),# invalid phone
        (["John", "123456789"], "Phone must have"),  # <10 digits
        (["John", "12345678901"], "Phone must have") # >10 digits
    ],
    ids=["no_phone","no_args","letters_in_phone","too_short","too_long"]
)
def test_add_contact_errors(args, expected_substr):
    book = make_book()
    msg = add_contact(args, book)
    assert expected_substr in msg

# -----------------------------------------------------------------------------
# change_contact
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args, initial, expected_phones",
    [
        (["John", "0123456789", "2222222222"],
         {"John": {"phones": ["0123456789"]}},
         ["2222222222"]),
        (["John Doe", "1111111111", "0000000000"],
         {"John Doe": {"phones": ["1111111111","3333333333"]}},
         ["3333333333","0000000000"]),
    ],
    ids=["single_phone","multi_phone"]
)
def test_change_contact_ok(args, initial, expected_phones):
    book = make_book(initial)
    msg = change_contact(args, book)
    assert msg == MSG_UPDATED
    rec = book.find(args[0])
    assert sorted([p.value for p in rec.get_phones()]) == sorted(expected_phones)

@pytest.mark.parametrize(
    "args, initial, expected_substr",
    [
        ([], {"John": {"phones": ["0123456789"]}}, MSG_ENTER_NAME_PHONE),
        (["John","0123456789","badphone"], {"John": {"phones": ["0123456789"]}}, "Phone must have"),
        (["John","9999999999","0000000000"], {"John": {"phones": ["0123456789"]}}, "Such number doesn't exist"),
        (["Mary","0123456789","0000000000"], {"John": {"phones": ["0123456789"]}}, MSG_NOT_FOUND),
    ],
    ids=["no_args","invalid_new_phone","old_phone_not_found","contact_not_found"]
)
def test_change_contact_errors(args, initial, expected_substr):
    book = make_book(initial)
    msg = change_contact(args, book)
    assert expected_substr in msg

# -----------------------------------------------------------------------------
# delete_contact
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args, initial, remaining_names",
    [
        (["John"], {"John": {"phones": ["0123456789"]}, "John Doe": {"phones": ["1111111111"]}}, ["John Doe"]),
        (["John Doe"], {"John": {"phones": ["0123456789"]}, "John Doe": {"phones": ["1111111111"]}}, ["John"]),
    ],
    ids=["delete_first","delete_second"]
)
def test_delete_contact_ok(args, initial, remaining_names):
    book = make_book(initial)
    msg = delete_contact(args, book)
    assert msg == MSG_DELETED
    assert sorted(list(book.data.keys())) == sorted(remaining_names)

@pytest.mark.parametrize(
    "args, initial, expected_substr",
    [
        ([], {"John": {"phones": ["0123456789"]}}, MSG_ENTER_NAME_PHONE),
        (["Mary"], {"John": {"phones": ["0123456789"]}}, MSG_NOT_FOUND),
    ],
    ids=["no_args","not_found"]
)
def test_delete_contact_errors(args, initial, expected_substr):
    book = make_book(initial)
    msg = delete_contact(args, book)
    assert expected_substr in msg

# -----------------------------------------------------------------------------
# delete_all
# -----------------------------------------------------------------------------

def test_delete_all_ok():
    book = make_book({"John": {"phones": ["0123456789"]}})
    msg = delete_all(book)
    assert msg == MSG_DELETED_ALL
    assert book.data == {}

def test_delete_all_errors():
    book = make_book()
    msg = delete_all(book)
    assert msg == MSG_NOT_FOUND

# -----------------------------------------------------------------------------
# show_phone
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "args, initial, expected_msg",
    [
        (["John"], {"John": {"phones": ["0123456789"]}}, "[name]John[/name]: [phone]0123456789[/phone]"),
        (["John Doe"], {"John Doe": {"phones": ["1111111111","2222222222"]}},
         "[name]John Doe[/name]: [phone]1111111111; 2222222222[/phone]"),
    ],
    ids=["single","multiple"]
)
def test_show_phone_ok(args, initial, expected_msg):
    book = make_book(initial)
    msg = show_phone(args, book)
    assert msg == expected_msg

@pytest.mark.parametrize(
    "args, initial, expected_substr",
    [
        ([], {"John": {"phones": ["0123456789"]}}, MSG_ENTER_NAME_PHONE),
        (["Mary"], {"John": {"phones": ["0123456789"]}}, MSG_NOT_FOUND),
    ],
    ids=["no_args","not_found"]
)
def test_show_phone_errors(args, initial, expected_substr):
    book = make_book(initial)
    msg = show_phone(args, book)
    assert expected_substr in msg

# -----------------------------------------------------------------------------
# show_all_cmd
# -----------------------------------------------------------------------------

def test_show_all_cmd_ok():
    book = make_book({
        "John": {"phones": ["0123456789"], "birthday": "05.11.2000"},
        "John Doe": {"phones": ["1111111111"]},
    })
    out = show_all_cmd([], book)
    # Пара точечных проверок: имена и форматы
    assert "Contact" in out
    assert "John" in out and "John Doe" in out
    assert "0123456789" in out
    assert "05.11.2000" in out

def test_show_all_cmd_empty():
    book = make_book()
    assert show_all_cmd([], book) == "No contacts."

# -----------------------------------------------------------------------------
# birthdays: add-birthday, show-birthday, birthdays list
# -----------------------------------------------------------------------------

def test_add_and_show_birthday_ok():
    book = make_book({"John": {"phones": ["0123456789"]}})
    msg = add_birthday(["John", "05.11.2000"], book)
    assert msg == "Birthday added."
    msg2 = show_birthday(["John"], book)
    assert msg2 == "05.11.2000"

def test_add_birthday_contact_not_found():
    book = make_book()
    msg = add_birthday(["John", "05.11.2000"], book)
    assert "Contact not found" in msg

def test_show_birthday_no_value():
    book = make_book({"John": {"phones": ["0123456789"]}})
    msg = show_birthday(["John"], book)
    assert msg == "No birthday set"

def test_birthdays_upcoming_contains_name_when_in_next_week():
    book = make_book({"John": {"phones": ["0123456789"]}})
    # birthday tomorrow
    tomorrow = datetime.today().date() + timedelta(days=1)
    date_str = tomorrow.strftime("%d.%m.%Y")
    add_birthday(["John", date_str], book)
    out = birthdays([], book)
    # at least name should be in output
    assert "John" in out

# -----------------------------------------------------------------------------
# parse_input
# -----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "input_data, expected_output",
    [
        ("add John 0123456789", ("add", ["John", "0123456789"])),
        (" change  John   0123456789  ", ("change", ["John", "0123456789"])),
        (" phone 'John Doe'", ("phone", ["John Doe"])),
        ("delete all", ("delete_all", [])),
        ("add-birthday John 05.11.2000", ("add-birthday", ["John", "05.11.2000"])),
        ("show-birthday John", ("show-birthday", ["John"])),
        ("birthdays", ("birthdays", [])),
    ],
    ids=["add","change_spaces","phone_quoted","delete_all","add_bday","show_bday","birthdays"]
)
def test_parse_input_ok(input_data, expected_output):
    output = parse_input(input_data)
    assert output == expected_output

@pytest.mark.parametrize(
    "input_data",
    [
        ("ttt"),
        (""),                  # empty string
        ("delete all phones"), # invalid command
    ],
    ids=["wrong_command","empty","wrong_delete"]
)
def test_parse_input_errors(input_data):
    with pytest.raises(ValueError):
        parse_input(input_data)

# -----------------------------------------------------------------------------
# process_line
# -----------------------------------------------------------------------------

def test_process_line_basic_ok():
    book = make_book()
    assert process_line("hello", [], book) == (MSG_HELLO, False)
    assert process_line("help", [], book) == (MSG_HELP, False)
    assert process_line("exit", [], book) == (MSG_GOODBYE, True)

def test_process_line_add_change_delete_flow():
    book = make_book()
    # add
    msg, flag = process_line("add", ["John", "0123456789"], book)
    assert msg == MSG_ADDED and flag is False
    # change
    msg, flag = process_line("change", ["John", "0123456789", "1111111111"], book)
    assert msg == MSG_UPDATED and flag is False
    # phone
    msg, flag = process_line("phone", ["John"], book)
    assert "[name]John[/name]" in msg and "1111111111" in msg
    # add-birthday
    tomorrow = (datetime.today().date() + timedelta(days=1)).strftime("%d.%m.%Y")
    msg, flag = process_line("add-birthday", ["John", tomorrow], book)
    assert msg == "Birthday added." and flag is False
    # show-birthday
    msg, flag = process_line("show-birthday", ["John"], book)
    assert msg == tomorrow and flag is False
    # delete
    msg, flag = process_line("delete", ["John"], book)
    assert msg == MSG_DELETED and flag is False

@pytest.mark.parametrize(
    "command",
    ["", "unknown"]
)
def test_process_line_errors(command):
    book = make_book()
    with pytest.raises(ValueError):
        process_line(command, [], book)

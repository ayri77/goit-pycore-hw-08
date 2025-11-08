# -----------------------------------------------------------------------
# -------------------------TASK DESCRIPTION------------------------------
# -----------------------------------------------------------------------
'''
☝ У цьому домашньому завданні ви повинні додати функціонал збереження адресної 
книги на диск та відновлення з диска.

Для цього ви маєте вибрати pickle протокол серіалізації / десеріалізації даних 
та реалізувати методи, які дозволять зберегти всі дані у файл і завантажити їх із файлу.

Головна мета — щоб застосунок не втрачав даних після виходу із застосунку та при 
запуску відновлював їх із файлу. Повинна зберігатися адресна книга, з якою ми працювали минулого разу.


Реалізуйте функціонал для збереження стану AddressBook у файл при закритті програми та відновлення стану при її запуску.

'''
# -----------------------------------------------------------------------
# -------------------------TASK SOLUTION---------------------------------
# -----------------------------------------------------------------------

from __future__ import annotations

import re
import shlex

from collections import UserDict
from typing import Callable
from functools import wraps

from datetime import datetime, timedelta
import pickle

import colorama
from colorama import Fore, Style

import sys
from pathlib import Path

# -----------------------------------------------------------------------
# ---------------------------Constants-----------------------------------
# -----------------------------------------------------------------------

STORAGE = "addressbook.pkl"

# Basic message
MSG_WELCOME = "Welcome to the assistant bot!"
MSG_HELLO = "How can I help you?"
MSG_ADDED = "Contact added."
MSG_DUPLICATED = "Contact already exist."
MSG_UPDATED = "Contact updated."
MSG_DELETED = "Contact deleted."
MSG_DELETED_ALL = "All contacts deleted."
MSG_NOT_FOUND = "Contact not found."
MSG_ENTER_NAME_PHONE = "Enter user name and phone"
MSG_INVALID = "Invalid command."
MSG_GOODBYE = "Good bye!"
MSG_CONFIRM = "Type YES to confirm: "
MSG_CANCEL = "Canceled."

COMMAND_YES = "YES"
# Commands with aliases
COMMANDS_HELLO = ["hello", "hi"]
COMMANDS_HELP = ["help"]
COMMANDS_ADD = ["add"]
COMMANDS_CHANGE = ["change"]
COMMANDS_DELETE = ["delete"] # "delete all" version
COMMANDS_PHONE = ["phone"]
COMMANDS_ALL = ["all"]
COMMANDS_EXIT = ["close", "exit"]
COMMANDS_ADD_BIRTHDAY = ["add-birthday"]
COMMANDS_SHOW_BIRTHDAY = ["show-birthday"]
COMMANDS_BIRTHDAYS = ["birthdays"]


# Short help (with marks)
MSG_HELP_SHORT = (
    "Assistant bot — команди:\n"
    "[cmd]hello[/cmd] | [cmd]hi[/cmd] — \"How can I help you?\"\n"
    "[cmd]help[/cmd] — показати довідку\n"
    "[cmd]add[/cmd] [arg]<ім’я>[/arg] [arg]<телефон>[/arg] — додати/перезаписати контакт\n"
    "[cmd]change[/cmd] [arg]<ім’я>[/arg] [arg]<новий_телефон>[/arg] — змінити номер\n"
    "[cmd]phone[/cmd] [arg]<ім’я>[/arg] — показати номер\n"
    "[cmd]delete[/cmd] [arg]<ім’я>[/arg] — видалити контакт\n"
    "[cmd]delete all[/cmd] — очистити всі контакти (підтвердіть [em]YES[/em])\n"
    "[cmd]all[/cmd] — показати всі контакти у форматі \"Name: phone\"\n"
    "[cmd]close[/cmd] | [cmd]exit[/cmd] — завершити роботу (\"Good bye!\")\n"
    "[cmd]add-birthday[/cmd] [arg]<ім’я>[/arg] [arg]<DD.MM.YYYY>[/arg] — додати день народження\n"
    "[cmd]show-birthday[/cmd] [arg]<ім’я>[/arg] — показати день народження\n"
    "[cmd]birthdays[/cmd] — хто має вітання протягом тижня\n"
    "Правила: команди без урахування регістру; імена у Title Case; дані пишуться в contacts.json при виході."
)

# Full help (with marks)
MSG_HELP = (
    "Assistant bot — довідка\n"
    "\n"
    "Основні команди:\n"
    "  [cmd]hello[/cmd] | [cmd]hi[/cmd]\n"
    "    Відповідь: \"How can I help you?\"\n"
    "\n"
    "  [cmd]help[/cmd]\n"
    "    Показати це повідомлення.\n"
    "\n"
    "  [cmd]add[/cmd] [arg]<ім’я>[/arg] [arg]<телефон>[/arg]\n"
    "    Додати або перезаписати контакт.\n"
    "    Приклад: [cmd]add[/cmd] [arg]John[/arg] [arg]123456789[/arg]\n"
    "\n"
    "  [cmd]change[/cmd] [arg]<ім’я>[/arg] [arg]<новий_телефон>[/arg]\n"
    "    Змінити номер існуючого контакту.\n"
    "    Приклад: [cmd]change[/cmd] [arg]John[/arg] [arg]0987654321[/arg]\n"
    "\n"
    "  [cmd]phone[/cmd] [arg]<ім’я>[/arg]\n"
    "    Показати номер телефону контакту.\n"
    "    Приклад: [cmd]phone[/cmd] [arg]John[/arg]\n"
    "\n"
    "  [cmd]delete[/cmd] [arg]<ім’я>[/arg]\n"
    "    Видалити контакт.\n"
    "    Приклад: [cmd]delete[/cmd] [arg]John[/arg]\n"
    "\n"
    "  [cmd]delete all[/cmd]\n"
    "    Очистити всі контакти (потрібне підтвердження: введіть [em]YES[/em]).\n"
    "\n"
    "  [cmd]all[/cmd]\n"
    "    Показати всі контакти у форматі \"Name: phone\".\n"
    "    Якщо контактів немає — \"No contacts.\".\n"
    "\n"
    "  [cmd]add-birthday[/cmd]\n"
    "    Додати день народження для контакту.\n"
    "    Приклад: [cmd]add-birthday[/cmd] [arg]John[/arg] [arg]25.12.1990[/arg]\n"
    "\n"
    "  [cmd]show-birthday[/cmd] [arg]<ім’я>[/arg]\n"
    "    Показати день народження контакту.\n"
    "    Приклад: [cmd]show-birthday[/cmd] [arg]John[/arg]\n"
    "\n"
    "  [cmd]birthdays[/cmd]\n"
    "    Показати, хто має вітання протягом тижня.\n"
    "\n"
    "  [cmd]close[/cmd] | [cmd]exit[/cmd]\n"
    "    Завершити роботу бота. Відповідь: \"Good bye!\".\n"
    "\n"
    "Правила:\n"
    "• Команди нечутливі до регістру.\n"
    "• Імена зберігаються у Title Case (напр.: \"john doe\" → \"John Doe\").\n"
    "• Імена з пробілами пишіть у лапках: add \"Mary Jane\" 12345"
    "• Дані зберігаються у файлі .contacts.json під час виходу."
    "• Не виконується контроль дублікатів."
)

# 
ERROR_MSG = {
    KeyError:  MSG_NOT_FOUND,
    IndexError: MSG_ENTER_NAME_PHONE,
    ValueError: MSG_INVALID,
}

# -----------------------------------------------------------------------
# ---------------------------Decorators-------------------------------------
# -----------------------------------------------------------------------

# input errors handling
def input_error(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (KeyError, IndexError, ValueError) as e:
            default = ERROR_MSG.get(type(e), "Input error")
            if isinstance(e, ValueError):
                msg = str(e).strip()
                return msg or default
            return default
    return wrapper

# -----------------------------------------------------------------------
# ---------------------------Utility-------------------------------------
# -----------------------------------------------------------------------


# -------------------- colorama formatting ------------------------------
TAGS = {
    "cmd": Fore.CYAN + Style.BRIGHT,
    "arg": Fore.MAGENTA,
    "em":  Style.BRIGHT,
    "name": Fore.LIGHTGREEN_EX,
    "phone": Fore.LIGHTMAGENTA_EX,
}
TAG_RE = re.compile(r"\[(cmd|arg|em|name|phone)\](.*?)\[/\1\]")

PALETTE = {
    "ok":   Fore.GREEN,
    "err":  Fore.RED,
    "info": Fore.CYAN,
    "warn": Fore.YELLOW,
}


def colorize_markers(text: str, kind: str | None = None) -> str:
    '''
    Colorize text markers [cmd], [arg], [em], [name], [phone]
    Args:
        text: input text with markers
        kind: optional kind for full text coloring
        Return:
        colored text
    '''
    def repl(m):
        tag, inner = m.group(1), m.group(2)
        return f"{TAGS[tag]}{inner}{Style.RESET_ALL}"
    colored = TAG_RE.sub(repl, text)

    if kind and kind in PALETTE:
        return f"{PALETTE[kind]}{colored}{Style.RESET_ALL}"
    return colored

# -----------------------------------------------------------------------
# ---------------------------Classes-----------------------------------
# -----------------------------------------------------------------------

# Base Field class
class Field:
    def __init__(self, value):
        self.value = self._normalize(value)

    def _normalize(self, v):
        return v

    def __str__(self):
        return str(self.value)
    
    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.value == other.value

# Name field with validation
class Name(Field):
    def _normalize(self, raw) -> str:
        s = re.sub(r'\s+', ' ', raw.strip())
        if not s:
            raise ValueError("Name is empty")
        return " ".join(p.capitalize() for p in s.split(" "))
      
# Phone field with validation
class Phone(Field):
    def _normalize(self, raw: str) -> str:
        digits = re.sub(r"\D", "", raw.strip())
        if len(digits) != 10:
            raise ValueError("Phone must have 10 digits")
        return digits

# Record class
# stores Name and list of Phones    
class Record:
    def __init__(self, name_str: str):
        self.name = Name(name_str)
        self._phones: list[Phone] = [] # incapsulated list of Phone objects
        self._birthday: Birthday | None = None  # Placeholder for birthday field

    def get_phones(self) -> tuple[Phone, ...]:
        # return a copy to prevent direct modification
        return tuple(self._phones)

    def add_phone(self, phone_str: str) -> None:        
        phone = Phone(phone_str)
        if phone in self._phones:
            raise ValueError("Such number exists for contact")
        else:
            self._phones.append(phone)

    def remove_phone(self, phone_str: str):
        phone = Phone(phone_str)
        if not phone in self._phones:
            raise ValueError("Such number doesn't exist for contact")
        else:
            self._phones.remove(phone)

    def edit_phone(self, phone_str: str, new_phone_str: str):
        phone = Phone(phone_str)
        new_phone = Phone(new_phone_str)
        if phone not in self._phones:
            raise ValueError("Such number doesn't exist for contact")
        if new_phone in self._phones:
            raise ValueError("New phone number already exists for contact")
        self._phones.remove(phone)
        self._phones.append(new_phone)

    def find_phone(self, phone_str: str) -> Phone:
        phone = Phone(phone_str)
        if not phone in self._phones:
            raise ValueError("Such number doesn't exist for contact")
        else:
            return self._phones[self._phones.index(phone)]
        
    def add_birthday(self, value: str) -> None:
        self._birthday = Birthday(value)

    @property
    def birthday(self) -> Birthday | None:
        return self._birthday

    def __str__(self):
        phones = "; ".join(p.value for p in self._phones) if self._phones else "—"
        bd = f", birthday: {self._birthday}" if self._birthday else ""
        return f"Contact name: {self.name.value}{bd}, phones: {phones}"
        
    def to_dict(self) -> dict:
        return {
            "name": self.name.value,
            "phones": [p.value for p in self._phones],
            "birthday": str(self._birthday) if self._birthday else None,
        }

    @staticmethod
    def from_dict(d: dict) -> "Record":
        rec = Record(d["name"])
        for ph in d.get("phones", []):
            rec.add_phone(ph)
        if d.get("birthday"):
            rec.add_birthday(d["birthday"])
        return rec    

# AddressBook class
# stores Records in UserDict
class AddressBook(UserDict):

    def __init__(self):
        super().__init__()

    def add_record(self, record: Record):
        if record.name.value in self.data:
            raise ValueError("Such name already exists in address book")
        
        self.data[record.name.value] = record

    def find(self, name_str:str) -> Record | None:
        # dont raise error if not found
        key = Name(name_str).value
        return self.data.get(key)

    def delete(self, name_str:str):
        try:
            key = Name(name_str).value
        except ValueError:
            raise KeyError("No such name in address book")
        del self.data[key]

    def get_upcoming_birthdays(self) -> list:        
        result = []
        today = datetime.today().date()
        end = today + timedelta(days=7)

        for rec in self.data.values():
            if not rec.birthday:
                continue
            b = rec.birthday.value.replace(year=today.year)
            if b < today:
                b = b.replace(year=today.year + 1)
            if today < b <= end:
                congr = b
                if congr.weekday() == 5:      # Saturday -> Monday
                    congr = congr + timedelta(days=2)
                elif congr.weekday() == 6:    # Sunday -> Monday
                    congr = congr + timedelta(days=1)
                result.append({
                    "name": rec.name.value,
                    "congratulation_date": congr.strftime("%d.%m.%Y")
                })
        result.sort(key=lambda x: (datetime.strptime(x["congratulation_date"], "%d.%m.%Y"), x["name"].lower()))
        return result
    
    # load pickle
    @classmethod
    def load_pickle(cls, path: str):
        '''
        load contacts from pickle file
        Args:
            path: path to pickle file
        '''
        try:
            with open(path, "rb") as f:
                obj = pickle.load(f)
            if not isinstance(obj, cls):
                return cls()
            return obj
        except FileNotFoundError:
            return cls()
            
    # save json
    def save_pickle(self, path: str):
        '''
        save contacts to pickle file
        Args:
            path: path to pickle file
        Return:
            None
        '''
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    def show_all(self) -> str:
        '''
        show all contacts in formatted table
        Return:
            formatted string with all contacts
        '''
        if not self.data:
            return "No contacts."
        lines = [
            "--------------------------|------------------------------|-----------------",
            "          Contact         |            Phones            |    Birthday     ",
            "--------------------------|------------------------------|-----------------",
        ]
        for name in sorted(self.data):
            rec = self.data[name]
            phones = "; ".join(p.value for p in rec.get_phones()) or "—"
            bday = str(rec.birthday) if rec.birthday else "—"
            lines.append(f"[name]{name:<26}[/name] [phone]{phones:<30}[/phone] {bday:>15}")
        return "\n".join(lines)


# Birthday field with validation
class Birthday(Field):
    def _normalize(self, raw: str):
        try:
            return datetime.strptime(raw.strip(), "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    def __str__(self):
        return self.value.strftime("%d.%m.%Y")

# -----------------------------------------------------------------------
# ---------------------------Handlers------------------------------------
# -----------------------------------------------------------------------

# add contact in datbase
@input_error
def add_contact(args: list[str], book: AddressBook) -> str:
    '''
    adding contact to contacts dict
    Args:
        args: list with name and phone
        book: AddressBook instance
    Return:
        message string
    '''
    if len(args) < 2:
        raise IndexError
    name, phone = args[0], args[1]
    rec = book.find(name)
    if rec is None:
        rec = Record(name)
        rec.add_phone(phone)
        book.add_record(rec)
        return MSG_ADDED
    rec.add_phone(phone)
    return MSG_UPDATED

# change contact phone
@input_error
def change_contact(args: list[str], book: AddressBook) -> str:
    '''
    changing contact phone in contacts dict
    Args:
        args: list with name and new phone
        book: AddressBook instance
    Return:
        message string
    '''
    if len(args) < 3:
        raise IndexError
    name, old_phone, new_phone = args[0], args[1], args[2]
    rec = book.find(name)
    if rec is None:
        raise KeyError(MSG_NOT_FOUND)
    rec.edit_phone(old_phone, new_phone)
    return MSG_UPDATED

# delete contact
@input_error
def delete_contact(args: list[str], book: AddressBook) -> str:
    '''
    deleting contact from contacts dict
    Args:
        args: list with name
        book: AddressBook instance
    Return:
        message string        
    '''
    if len(args) != 1:
        raise IndexError    
    book.delete(args[0])
    return MSG_DELETED

@input_error
def delete_all(book: AddressBook) -> str:
    '''
    deleting all contacts from contacts dict
    Args:
        book: AddressBook instance
    Return:
        message string
    '''
    if not book.data:
        raise KeyError(MSG_NOT_FOUND)
    book.data.clear()
    return MSG_DELETED_ALL

@input_error
def show_phone(args: list[str], book: AddressBook) -> str:
    '''
    showing contact phone from contacts dict
    Args:
        args: list with name
        book: AddressBook instance
    Return:
        message string
    '''
    if len(args) != 1:
        raise IndexError
    rec = book.find(args[0])
    if rec is None:
        raise KeyError(MSG_NOT_FOUND)
    phones = [p.value for p in rec.get_phones()]
    return f"[name]{rec.name.value}[/name]: [phone]{'; '.join(phones) if phones else '—'}[/phone]"

@input_error
def show_all_cmd(_args: list[str], book: AddressBook) -> str:
    return book.show_all()

# --- new handlers ---

@input_error
def add_birthday(args: list[str], book: AddressBook) -> str:
    if len(args) < 2:
        raise IndexError
    name, date_str = args[0], args[1]
    rec = book.find(name)
    if rec is None:
        raise KeyError("Contact not found")
    rec.add_birthday(date_str)
    return "Birthday added."

@input_error
def show_birthday(args: list[str], book: AddressBook) -> str:
    if len(args) != 1:
        raise IndexError
    rec = book.find(args[0])
    if rec is None:
        raise KeyError("Contact not found")
    return str(rec.birthday) if rec.birthday else "No birthday set"

@input_error
def birthdays(_args: list[str], book: AddressBook) -> str:
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays in the next week."
    lines = ["Upcoming birthdays in the next week:"]
    for entry in upcoming:
        lines.append(f"{entry['congratulation_date']} — {entry['name']}")
    return "\n".join(lines)

# -----------------------------------------------------------------------
# ---------------------------Interface-----------------------------------
# -----------------------------------------------------------------------

# parsing message from user
# return command and arguments
def parse_input(user_input: str) -> tuple[str, list[str]]:
    '''
    Args:
        user input string
    Return     
        command 
        args list
    '''
    user_input = user_input.strip()
    if user_input == "":
        raise ValueError(MSG_INVALID)    
    
    try:
        cmd, *args = shlex.split(user_input)
    except ValueError:
        raise ValueError(MSG_INVALID)
    
    cmd = cmd.strip().lower()

    if args == []:
        # commands without args
        if cmd in COMMANDS_HELLO:
            return ("hello", [])
        elif cmd in COMMANDS_HELP:
            return ("help", [])
        elif cmd in COMMANDS_EXIT:
            return ("exit", [])
        elif cmd in COMMANDS_ALL:
            return ("show_all",[])
        elif cmd in COMMANDS_BIRTHDAYS:
            return ("birthdays", [])        
        else:
            raise ValueError(MSG_INVALID)
    else:
        # commands with args
        args_count  = len(args)
        if cmd in COMMANDS_ADD:
            return ("add", args)
        elif cmd in COMMANDS_DELETE and args_count == 1 and args[0].strip() == "all":            
            return ("delete_all", [])
        elif cmd in COMMANDS_DELETE and args_count == 1:
            return ("delete", [args[0].strip()])
        elif cmd in COMMANDS_PHONE:
            return ("phone", [args[0].strip()])
        elif cmd in COMMANDS_CHANGE:
            return ("change", args)
        elif cmd in COMMANDS_ADD_BIRTHDAY:
            return ("add-birthday", args)
        elif cmd in COMMANDS_SHOW_BIRTHDAY:
            return ("show-birthday", args)
        else:
            raise ValueError(MSG_INVALID)

# processing command
def process_line(command, args, book: AddressBook) -> tuple[str, bool]:
    '''
    Args:
        command
        arguments
    Return:
        answer message
        boolean exit flag
    '''
    if command == "hello":
        return (MSG_HELLO, False)
    elif command == "help":
        return (MSG_HELP, False)
    elif command == "exit":
        return (MSG_GOODBYE, True)
    elif command == "phone":
        return (show_phone(args, book), False)
    elif command == "add":
        return (add_contact(args, book), False)
    elif command == "change":
        return (change_contact(args, book), False)
    elif command == "delete":
        return (delete_contact(args, book), False)
    elif command == "delete_all":
        return (delete_all(book), False)
    elif command == "show_all":
        return (show_all_cmd(args, book), False)
    elif command == "add-birthday":
        return (add_birthday(args, book), False)
    elif command == "show-birthday":
        return (show_birthday(args, book), False)
    elif command == "birthdays":
        return (birthdays(args, book), False)
    else:
        raise ValueError(MSG_INVALID)

# -----------------------------------------------------------------------
# -----------------------------main--------------------------------------
# -----------------------------------------------------------------------

def main():
    
    colorama.init(autoreset=True)

    book = AddressBook()

    # loading contacts
    book = AddressBook.load_pickle(STORAGE)
    
    '''
    if Path(STORAGE).exists():
        try:
            book.load_contacts(STORAGE)
        except (json.JSONDecodeError, OSError):
            print(colorize_markers("Error loading contacts file.", "err"))
    '''

    # Welcome message
    print(colorize_markers(MSG_WELCOME, "info"))
    print(colorize_markers(MSG_HELP_SHORT, "info"))
        
    while True:
        # while not exit command cycle
        input_data = input("Enter a command: ")
        try:
            command, args = parse_input(input_data)
        except ValueError as e:
            print(colorize_markers(str(e), "err"))  # "Invalid command."
            continue        

        if command == "delete_all":
            input_data = input((colorize_markers(MSG_CONFIRM, "warn")))
            if input_data.upper() != COMMAND_YES:
                print(colorize_markers(MSG_CANCEL,"warn"))
                continue

        try:
            answer, exit_flag = process_line(command, args, book)
        except ValueError as e:
            print(colorize_markers(str(e), "err"))
            continue
            
        kind = (
            "ok"   if answer in (MSG_ADDED, MSG_UPDATED, MSG_DELETED, MSG_DELETED_ALL, MSG_GOODBYE)
            else "err"  if answer in (MSG_INVALID, MSG_NOT_FOUND, MSG_DUPLICATED) or answer.lower().startswith("usage:")
            else "info" if answer in (MSG_HELP, MSG_HELP_SHORT, MSG_HELLO, MSG_WELCOME)
            else "warn" if "no contacts" in answer.lower()
            else None
        )
        print(colorize_markers(answer, kind))

        if exit_flag:
            book.save_pickle(STORAGE)
            sys.exit(0)      

if __name__ == "__main__":
    main()

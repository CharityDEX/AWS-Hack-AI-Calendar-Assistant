from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import base64
from email.mime.text import MIMEText
import os
from langchain.tools import BaseTool, StructuredTool, tool
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from pydantic import BaseModel, Field
from typing import List, Tuple
import json

CREDENTIALS_OAUTH = "credentials-oauth.json"
TOKEN_FILE = "token.json"
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
date_time_format = "%Y-%m-%d %H:%M:%S"
date_format = "%Y-%m-%d"
time_format = "%H:%M:%S"

def authenticate_user():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as token_file:
            try:
                data = json.load(token_file)
                creds = Credentials.from_authorized_user_info(data, SCOPES)
            except json.JSONDecodeError:
                print("Invalid token file. Please re-authenticate.")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_OAUTH, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, 'w') as token_file:
            token_file.write(creds.to_json())
    return creds

def dates_to_strings(dates):
    string_tuples = []
    for slot_start, slot_end in dates:
        string_tuples.append((slot_start.strftime(date_time_format), slot_end.strftime(date_time_format)))
    return string_tuples

def pst_to_utc(pst_datetime):
    """Convert a naive datetime object from PST (UTC-8) to naive UTC."""
    pst_offset = timedelta(hours=8)
    utc_time = pst_datetime + pst_offset
    return utc_time

def utc_to_pst(utc_datetime):
    """Convert a naive datetime object from UTC to naive PST (UTC-8)."""
    pst_offset = timedelta(hours=-8)
    pst_time = utc_datetime + pst_offset
    return pst_time

def get_availability_slots(participant_emails: list[str], meeting_interval_start_date: str, meeting_interval_end_date: str, meeting_duration_minutes: int) -> list[tuple[str]]:
    start_date = datetime.strptime(meeting_interval_start_date, date_time_format)
    end_date = datetime.strptime(meeting_interval_end_date, date_time_format)
    start_date = pst_to_utc(start_date)
    end_date = pst_to_utc(end_date)
    body = {
        "timeMin": start_date.isoformat() + "Z",
        "timeMax": end_date.isoformat() + "Z",
        "items": [{"id": email} for email in participant_emails]
    }
    freebusy_result = calendar_service.freebusy().query(body=body).execute()
    all_busy_periods = []
    for calendar in freebusy_result['calendars'].values():
        for busy_period in calendar.get('busy', []):
            busy_start = datetime.fromisoformat(busy_period['start'][:-1])
            busy_end = datetime.fromisoformat(busy_period['end'][:-1])
            all_busy_periods.append((busy_start, busy_end))
    all_busy_periods.sort()
    merged_busy_periods = []
    for busy_start, busy_end in all_busy_periods:
        if not merged_busy_periods or merged_busy_periods[-1][1] < busy_start:
            merged_busy_periods.append((busy_start, busy_end))
        else:
            merged_busy_periods[-1] = (merged_busy_periods[-1][0], max(merged_busy_periods[-1][1], busy_end))
    available_slots = []
    current_start = start_date
    for busy_start, busy_end in merged_busy_periods:
        if busy_start - current_start >= timedelta(minutes=meeting_duration_minutes):
            available_slots.append((utc_to_pst(current_start), utc_to_pst(busy_start)))
        current_start = busy_end
    if end_date - current_start >= timedelta(minutes=meeting_duration_minutes):
        available_slots.append((utc_to_pst(current_start), utc_to_pst(end_date)))
    return dates_to_strings(available_slots)

def schedule_slots(email_addresses: list[str], start_datetime: str, end_datetime: str, meeting_duration: int):
    load_dotenv()
    creds = authenticate_user()
    global calendar_service
    calendar_service = build('calendar', 'v3', credentials=creds)
    global email_service
    email_service = build('gmail', 'v1', credentials=creds)
    
    class CalendarResponse(BaseModel):
        suggested_slots: List[List[str]] = Field(description="List of available time slots in format [start_date, start_time, end_date, end_time]")

    llm = ChatBedrock(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_kwargs=dict(temperature=0),
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name="us-west-2"
    ).with_structured_output(CalendarResponse)


    available_slots = get_availability_slots(email_addresses, start_datetime, end_datetime, meeting_duration)
    # print(slots)
    response = llm.invoke(f"You are a calendar scheduling assistant. Please suggest at most 6 possible time slots and return them as a list of lists containing start - end date time pairs with format start_date, start_time, end_date, end_time [{date_format},{time_format},{date_format},{time_format}]. Return the lists and nothing else. Keep in mind the context is a university environment and keep meetings between 8am - 8pm. Suggest the most reasonable and convenient time slots to schedule meetings. Here are the available time slots for a {meeting_duration}-minute meeting: {available_slots}. ")
    
    return {
        "email_addresses": email_addresses,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "meeting_duration": meeting_duration,
        "suggested_slots": response.suggested_slots
    }

def main():
    result = schedule_slots(
        ["sfigueira@scu.edu", "swu12@scu.edu"],
        "2024-11-14 09:00:00",
        "2024-11-15 20:00:00",
        45
    )
    print("Suggested slots:", result["suggested_slots"])
    print("Returned elements", result)

if __name__ == "__main__":
    main()


from dotenv import load_dotenv
import os
load_dotenv()
import asyncio
import base64
import time
from langgraph.prebuilt import create_react_agent
from langchain_google_community import GmailToolkit
from langchain_google_community.gmail.utils import get_gmail_credentials, build_resource_service
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import Annotated
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import OpenAI
from langchain_core.output_parsers.string import StrOutputParser
import re
from typing import Union
import requests
import aiohttp
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import OpenAI
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
import gradio as gr
from gradio import ChatMessage
from langgraph.graph import StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta, timezone
import app
from pydantic import BaseModel, Field
from googleapiclient.errors import HttpError

format_string = "%Y-%m-%d %H:%M:%S"


email_llm = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    model_kwargs=dict(temperature=0),
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name="us-west-2",
    beta_use_converse_api=True
    # other params...
)
'''
classifier_llm = ChatBedrock(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    model_kwargs=dict(temperature=0),
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name="us-west-2",
    beta_use_converse_api=True
    # other params...
)'''

class ConfirmationFormat(BaseModel):
   classification: int = Field(description="Classification of the email: 0 for confirmation, 1 for denial, 2 for unrelated")

#email_llm = ChatOpenAI(temperature=0)
classifier_llm = ChatOpenAI(temperature=0).with_structured_output(ConfirmationFormat)
extractor_llm = ChatOpenAI(temperature=0)

# Graph State
class GraphState(TypedDict):
    graph_start_time: str
    meeting_slot_start: str
    meeting_slot_end: str
    participant_info: dict[str, tuple[bool, str]] # key: email value: (confirmed, last datetime sent)
    meeting_duration_minutes: int
    meeting_description: str
    organizer_name: str
    organizer_email: str
    access_token: str
    refresh_token: str
    background_task_running: bool
    last_email_check_time: str
    blocked_slots: str
    meeting_title: str

def get_now_string():
    now = utc_to_pst(datetime.now(timezone.utc))
    now = now - timedelta(minutes=2)
    now_string = now.strftime(format_string)
    return now_string

def pst_to_utc(pst_datetime):
    """Convert a naive datetime object from PST (UTC-8) to naive UTC."""
    # Define the UTC offset for PST (UTC-8)
    pst_offset = timedelta(hours=8)
    
    # Localize the naive datetime to PST and convert it to UTC
    utc_time = pst_datetime + pst_offset
    
    # Return as naive UTC datetime (without tzinfo)
    return utc_time

def utc_to_pst(utc_datetime):
    """Convert a naive datetime object from UTC to naive PST (UTC-8)."""
    # Define the UTC offset for PST (UTC-8)
    pst_offset = timedelta(hours=-8)
    
    # Localize the naive datetime to UTC and convert it to PST
    pst_time = utc_datetime + pst_offset
    
    # Return as naive PST datetime (without tzinfo)
    return pst_time

# FIRST NODE
def send_emails(state: GraphState):
    print("\n\nSTARTED GRAPH!\n\n")
    creds = Credentials(token=state["access_token"], refresh_token=state["refresh_token"], client_id=os.environ["GOOGLE_CLIENT_ID"], client_secret=os.environ["GOOGLE_CLIENT_SECRET"])
    email_service = build_resource_service(credentials=creds)

    toolkit = GmailToolkit(api_resource=email_service)
    tools = toolkit.get_tools()
    send_tool = tools[1]

    react_graph = create_react_agent(model=email_llm, tools=[send_tool])

    emails = state["participant_info"].keys() #TODO list() ?
    org_name = state["organizer_name"]
    duration = state["meeting_duration_minutes"]
    slot_start = state["meeting_slot_start"]
    slot_end = state["meeting_slot_end"]
    meeting_description = state["meeting_description"]
    meeting_title = state["meeting_title"]

    print("\n\nEMAILS:\n\n" + str(emails))

    send_email_prompt = f'''
        You are a specialized email-sending assistant. Please send a nice email to each of the provided participants individually, 
        asking them if they are able to attend the meeting. The meeting will last {duration} minutes.
        The meeting will start during this time and date: {slot_start} and will last until: {slot_end}.
        Here is the list of emails: {str(emails)} make sure to send each one individually and personalize it!
        Your name is {org_name}. This is the meeting description (use as reference): {meeting_description}.
        The meeting is called {meeting_title}, put this in the subject line of the emails.
        REFER TO THE RECIPIENTS ONLY BY THEIR EMAIL! DO NOT USE THEIR NAMES! Example: Hello abc@email.com, ... 
        If there is only one recipient, please send only one email; DO NOT SEND MULTIPLE EMAILS TO THE SAME PARTICIPANT!
    '''
    print("\nSENDING EMAILS:\n")
    graph_input = {"messages": [("user", send_email_prompt)]}
    react_graph.invoke(graph_input)
    print("\n EMAILS SENT!!!\n")

    # emails have been sent hopefully
    # next: invoke the async part

def get_full_email(message, email_service):
    msg_id = message["id"]
    full_email = email_service.users().messages().get(userId='me', id=msg_id, format='full').execute()

    payload = full_email.get('payload', {})
    headers = payload.get('headers', [])

    subject = next((header['value'] for header in headers if header['name'] == 'Subject'), "No Subject")

    # Extract the email body
    body = ""
    parts = payload.get('parts', [])
    for part in parts:
        if part['mimeType'] == 'text/plain':  # Plain text body
            body = part.get('body', {}).get('data', "")
        elif part['mimeType'] == 'text/html':  # HTML body
            body = part.get('body', {}).get('data', "")

    # Decode the body if it's Base64 encoded
    if body:
        body = base64.urlsafe_b64decode(body).decode('utf-8')
    
    return [subject, body]


def classify_email(slot_start, slot_end, subject, body):
    classify_email_prompt = f'''
        You are a specialized email-classification assistant. We have previously
        contacted this person to ask them if they are available
        for a meeting that starts at {slot_start} and ends at {slot_end}.
        The email provided might be a response from the user confirming the meeting, or it could be
        denying the meeting at this time, or it could be something totally unrelated.
        Here is the email subject: {subject}
        Here is the email body: {body}
        Please classify this email, output a 0 if it is a confirmation, 1 if it is denial, or 2 if it is unrelated.
        OUTPUT ONLY ONE INTEGER DO NOT WRITE ANYHTING ELSE
        Example: 0
        Classification Integer:
    '''

    response = classifier_llm.invoke(classify_email_prompt)
    return response

# SECOND NODE (stalls)
def email_listener(state: GraphState):

    async def long_running_task(config, localstate):
        print("Task started...")
        #state = app.email_graph.get_state(config=config).values

        client_id = os.environ["GOOGLE_CLIENT_ID"]
        client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
        creds = Credentials(token=localstate["access_token"], refresh_token=localstate["refresh_token"], client_id=client_id, client_secret=client_secret)
        email_service = build_resource_service(credentials=creds)

        while localstate["background_task_running"]:
            #state = app.email_graph.get_state(config=config).values
            last_check_time_str = localstate["last_email_check_time"]
            print("LAST CHECK: " + last_check_time_str)
            last_check_time = datetime.strptime(last_check_time_str, format_string)
            last_check_time_utc = last_check_time#pst_to_utc(last_check_time)

            participants = localstate["participant_info"]

            for sender, info in participants.items():
                
                # get emails
                query = f'after:{int(last_check_time_utc.timestamp())} from:{sender}'
                response = email_service.users().messages().list(
                    userId='me',
                    q=query
                ).execute()

                messages = response.get('messages', [])

                # classify email bodies
                for message in messages:
                    print("GOT AN EMAIL, PROCESSING IT!")
                    full_email = get_full_email(message, email_service)
                    subject = full_email[0]
                    body = full_email[1]

                    # classify the email
                    response = classify_email(localstate["meeting_slot_start"], localstate["meeting_slot_end"], subject, body)
                    print("CLASSIFIED EMAIL AS: " + str(response.classification))

                    if (response.classification == 0):
                        print("USER HAS CONFIRMED!!!")
                        # update state (user has confirmed)
                        info_buf = localstate["participant_info"]
                        info_buf[sender] = (True, get_now_string())

                        print("HERE IS THE DICTIONARY: " + str(info_buf))

                        # check if all are confirmed
                        all_confirmed = True
                        print("INFOBUF: " + str(info_buf))
                        for k, v in info_buf.items():
                            print("USER: " + str(k) + " VALUE: " + str(v[0]))
                            if v[0] == False:
                                all_confirmed = False

                        print("ALL CONFIRMED: " + str(all_confirmed))
                            
                        if all_confirmed:
                            # STOP ASYNC
                            #app.email_graph.update_state(config=config, values={"background_task_running": False})
                            print("ALL HAVE CONFIRMED SO STOPPING")
                            localstate["background_task_running"] = False
                            localstate["schedule_success"] = True
                            return localstate
                        else:
                            #app.email_graph.update_state(config=config, values={"participant_info": info_buf})
                            localstate["participant_info"] = info_buf
                    elif (response.classification == 1):
                        print("USER HAS DENIED!!!")
                        localstate["background_task_running"] = False
                        localstate["schedule_success"] = False
                        return localstate
                        #on_user_deny(localstate, subject, body)
            
            # check cycle done, update last check time
            #app.email_graph.update_state(config=config, values={"last_email_check_time": get_now_string()})
            localstate["last_email_check_time"] = get_now_string()
            print("\nUpdated last check to: " + str(localstate["last_email_check_time"]))
            
            # sleep for 2 minutes
            await asyncio.sleep(10)
    
    #bg_flag = state["is_bgtask_running"]
    #if not bg_flag:
    #    bg_flag = True
    #    background_task = asyncio.create_task(long_running_task())
    #    background_task.add_done_callback(on_task_done)

    # launch the background task
    config = {"configurable": {"thread_id": state["organizer_email"]}}

    # populate state first
    app.email_graph.update_state(config=config, values={"background_task_running": True})
    info_buf = state["participant_info"]
    for k, v in info_buf.items():
        info_buf[k] = (False, get_now_string())
    app.email_graph.update_state(config=config, values={"participant_info": info_buf})
    app.email_graph.update_state(config=config, values={"last_email_check_time": str(get_now_string())})

    # now launch
    new_state_vals = app.email_graph.get_state(config=config).values
    background_task = asyncio.create_task(long_running_task(config, new_state_vals))
    background_task.add_done_callback(on_task_done)
    print("\nLaunched Task\n")

def on_task_done(task):
    state = task.result()
    # CALL THE EVENT SCHEDULER
    
    if state.get("schedule_success", False):
        create_event(state)

    #config = {"configurable": {"thread_id": state["email"]}}
    #print(f"EMAIL in function on_task: {state["email"]}")
    #bot.rag_graph.update_state(config=config, values={"is_bgtask_running": False})
    #print(f"Callback: Task finished with result: {background_task.result()}")
    print("\nprocess ended ")

def create_event(state):
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
    creds = Credentials(token=state["access_token"], refresh_token=state["refresh_token"], client_id=client_id, client_secret=client_secret)
    service = build('calendar', 'v3', credentials=creds)

    start_time = datetime.strptime(state["meeting_slot_start"], format_string)
    end_time = datetime.strptime(state["meeting_slot_end"], format_string)
    emails = list(state["participant_info"].keys())
    print("\nEMAILS: " + str(emails) + "\n")
    emails.append(state["organizer_email"])
    attendees = [{'email': email} for email in emails]

    print("\nATTENDEES: " + str(attendees) + "\n")

    # create event
    event = {
        'summary': state["meeting_title"],
        'description': state["meeting_description"],
        'start': {
            'dateTime': start_time.isoformat(),  # Start time (ISO format)
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': end_time.isoformat(),  # End time (ISO format)
            'timeZone': 'America/Los_Angeles'
        },
        'attendees': attendees,
        'reminders': {
            'useDefault': True
        }
    }

    try:
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
    except HttpError as error:
        print(f"An error occurred: {error}")

def on_user_deny(localstate, subject, body):

    #time_slots = extract_blocking_slots(subject, body, localstate["meeting_slot_start"], localstate["meeting_slot_end"])

    print("user denied, ending")
    # TODO maybe write email to organizer saying denied?


    # DENIAL PLAN:
    # 1. extract blocking slots from the denial email with llm
    #        (tell it that if cant find, use the default time given)
    # 2. call sean's calendar func with http with all data + blocking slot
    #          (version that does not need buttons but just triggers graph)

    # http call to sean's calendar function, but add non-working slots

def extract_blocking_slots(subject, body, slot_start, slot_end):

    current_datetime = None
    current_day_of_week = None

    extract_slots_prompt = f'''
        You are a specialized time slot extractor assistant. You will be provided an email
        that denies a meeting confirmation. Please check if the email specifies what time slots
        the person can not meet during, and return those time slots. For example, if the email
        says "I am busy Nov 13", return that whole day as a time slot. If the email does not
        specify when the person is busy and just says they can't attend the meeting, return
        the following time slot: {slot_start, slot_end}
        Generate only a time slot! For context it is currently {current_datetime} {current_day_of_week}
        TIME SLOT:
    '''

    response = extractor_llm.invoke(extract_slots_prompt)
    return response

# Build Graph
def create_email_graph():
    graph_builder = StateGraph(GraphState)

    graph_builder.add_node("send_emails", send_emails)
    graph_builder.add_node("email_listener", email_listener)

    graph_builder.add_edge(START, "send_emails")
    graph_builder.add_edge("send_emails", "email_listener")
    graph_builder.add_edge("email_listener", END)

    #memory = MemorySaver()

    # Create a connection to the SQLite database
    conn = sqlite3.connect("checkpoints.sqlite",check_same_thread=False)
    memory = SqliteSaver(conn)

    graph = graph_builder.compile(checkpointer=memory)
    return graph

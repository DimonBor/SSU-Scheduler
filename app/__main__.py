import os
import os.path
import json
import time
import logging
import schedule
import requests
import datetime
import dateutil.tz as dtz
from dateutil.relativedelta import relativedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class ContinueI(Exception):
    pass


logging.basicConfig(level="INFO")
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL:@SECLEVEL=1'
continueI = ContinueI()
creds = None

SCHEDULE_PERIOD = int(os.getenv('SCHEDULE_PERIOD')) if os.getenv('SCHEDULE_PERIOD') else 14
GROUP_CODE = int(os.getenv('GROUP_CODE'))           if os.getenv('GROUP_CODE')      else 1002732
POPUP_REMINDER = int(os.getenv('POPUP_REMINDER'))   if os.getenv('POPUP_REMINDER')  else 10
UPDATE_TIMEOUT = int(os.getenv('UPDATE_TIMEOUT'))   if os.getenv('UPDATE_TIMEOUT')  else 60
SCOPES = ['https://www.googleapis.com/auth/calendar']


def getSchedule():
    Data = {
        "id_grp": GROUP_CODE,
        "date_beg": (datetime.date.today()).strftime("%d.%m.%Y"),
        "date_end": (
            datetime.date.today() + relativedelta(days=SCHEDULE_PERIOD)
        ).strftime("%d.%m.%Y")
    }   # Creating payload for selected period 

    try:
        response = requests.post(
            'https://schedule.sumdu.edu.ua/index/json',
            data=Data,
            verify=False,
            timeout=10
        )
    except:
        logging.error(f"[{datetime.datetime.now()}]: Error of SSU Schedule")

    return json.loads(response.text)


def updateEvents():
    scheduleJSON = getSchedule()

    try:
        service = build('calendar', 'v3', credentials=creds)

        for ssuEvent in scheduleJSON:
            if not ssuEvent['NAME_DISC']: continue

            timeStart = datetime.datetime.strptime(     # Converting Schedule timeframe to isoformat
                f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][:5]}",
                "%d.%m.%Y %H:%M"
            ).replace(tzinfo=dtz.gettz("Europe/Kyiv")).isoformat()

            timeEnd = datetime.datetime.strptime(       # Converting Schedule timeframe to isoformat
                f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][6:]}",
                "%d.%m.%Y %H:%M"
            ).replace(tzinfo=dtz.gettz("Europe/Kyiv")).isoformat()

            checkEventsResult = service.events().list(      # Check if events
                calendarId='primary',                       # already created
                timeMin=timeStart,
                timeMax=timeEnd,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = checkEventsResult.get('items', [])     

            try:
                for entry in events:    # Checking if event already scheduled
                    if entry['summary'] == ssuEvent['NAME_DISC']:
                        raise continueI
            except ContinueI:
                continue


            event = {   # Creating event payload
                'summary': ssuEvent['NAME_DISC'],
                'location': ssuEvent['NAME_AUD'] if ssuEvent['NAME_AUD'] else 'Online',
                'description': f"{ssuEvent['NAME_FIO']}\n{ssuEvent['NAME_STUD']}",
                'start': {
                    'dateTime': timeStart,
                    'timeZone': 'Europe/Kyiv',
                },
                'end': {
                    'dateTime': timeEnd,
                    'timeZone': 'Europe/Kyiv',
                },
                'recurrence': None,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': POPUP_REMINDER},
                    ],
                },
            }

            event = service.events().insert(    # Executing API call
                calendarId='primary',
                body=event
            ).execute()

            logging.info(f"[{datetime.datetime.now()}]: Event created: {event.get('htmlLink')}")

    except HttpError as error:
        logging.error(f"[{datetime.datetime.now()}]: {error}")


def main():

    # Stolen from Google examples
    global creds

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(
            'token.json', 
            SCOPES
        )
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'creds/credentials.json', 
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    logging.info(
        f"[{datetime.datetime.now()}]: Starting schedule.\n" +
        "\tParams:\n" +
        f"\t\tSCHEDULE_PERIOD: {SCHEDULE_PERIOD}\n" +
        f"\t\tGROUP_CODE: {GROUP_CODE}\n" +
        f"\t\tPOPUP_REMINDER: {POPUP_REMINDER}\n" +
        f"\t\tUPDATE_TIMEOUT: {UPDATE_TIMEOUT}\n"
    )

    while True:     # Running scheduler
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    schedule.every(UPDATE_TIMEOUT).minutes.do(updateEvents)
    main()

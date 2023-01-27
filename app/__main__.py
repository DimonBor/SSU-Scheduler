import os
import os.path
import json
import requests
import datetime
import dateutil.tz as dtz
from dateutil.relativedelta import relativedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'ALL:@SECLEVEL=1'

SCHEDULE_PERIOD = int(os.getenv('SCHEDULE_PERIOD'))
GROUP_CODE = int(os.getenv('GROUP_CODE'))  # 1002732
POPUP_REMINDER = int(os.getenv('POPUP_REMINDER'))
SCOPES = ['https://www.googleapis.com/auth/calendar']


def getSchedule():
    Data = {
        "id_grp": GROUP_CODE,
        "date_beg": (datetime.date.today()).strftime("%d.%m.%Y"),
        "date_end": (
            datetime.date.today() + relativedelta(days=SCHEDULE_PERIOD)
        ).strftime("%d.%m.%Y")
    }

    response = requests.post(
        'https://schedule.sumdu.edu.ua/index/json',
        data=Data,
        verify=False,
        timeout=10
    )

    return json.loads(response.text)


def updateEvents(creds):
    scheduleJSON = getSchedule()

    try:
        service = build('calendar', 'v3', credentials=creds)

        for ssuEvent in scheduleJSON:
            if not ssuEvent['NAME_DISC']: continue

            timeStart = datetime.datetime.strptime(
                f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][:5]}",
                "%d.%m.%Y %H:%M"
            ).replace(tzinfo=dtz.gettz("Europe/Kyiv")).isoformat()

            timeEnd = datetime.datetime.strptime(
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

            if events:
                continue

            event = {
                'summary': ssuEvent['NAME_DISC'],
                'location': ssuEvent['NAME_AUD'] if ssuEvent['NAME_AUD'] else 'Online',
                'description': ssuEvent['NAME_FIO'],
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

            event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            print('Event created: %s' % (event.get('htmlLink')))

    except HttpError as error:
        print('An error occurred: %s' % error)


def main():

    # Stolen from Google examples
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    updateEvents(creds)


if __name__ == '__main__':
    main()

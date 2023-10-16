import datetime
import json
import logging
import dateutil.tz as dtz
import requests

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db_utils import get_users, get_access_token


def get_schedule(group_code, schedule_period):
    data = {
        "method": "getSchedules",
        "id_grp": group_code,
        "date_beg": (datetime.date.today()).strftime("%d.%m.%Y"),
        "date_end": (
                datetime.date.today() + datetime.timedelta(days=schedule_period)
        ).strftime("%d.%m.%Y")
    }  # Creating payload for selected period

    try:
        response = requests.post(
            'https://schedule.sumdu.edu.ua/index/json',
            params=data,
            verify=False,
            timeout=10
        )
    except:
        logging.error(f"[{datetime.datetime.now()}]: Error of SSU Schedule")
        return None

    return json.loads(response.text)


def update_events():

    logging.info(f"[{datetime.datetime.now()}]: Starting updates.")

    time_start = datetime.datetime.now()

    for user in get_users():
        try:

            schedule_events = get_schedule(user.group_code, user.fetch_days)

            service = build('calendar', 'v3', credentials=Credentials(token=get_access_token(user)))

            calendars_list = service.calendarList().list().execute()
            calendars = calendars_list.get('items', [])

            for entry in calendars:
                if entry['summary'] == 'SSU Schedule':
                    service.calendars().delete(calendarId=entry['id']).execute()  # deleteing previous calendar
                    # Deleting is needed because clear() works only for primary calendar (WTF Google?)
                    # So that schedule may change, and we need to recreate the calendar in each iteration

            calendar_id = service.calendars().insert(body={'summary': 'SSU Schedule'}).execute()['id']
            # Creating the calendar

            service.calendarList().update(  # Enable the calendar in list and update color to much SSU style
                calendarId=calendar_id,
                body={
                    'colorId': '16',
                    'selected': True
                }).execute()

            for ssuEvent in schedule_events:
                if not ssuEvent['NAME_DISC']: continue

                timeStart = datetime.datetime.strptime(  # Converting Schedule timeframe to isoformat
                    f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][:5]}",
                    "%d.%m.%Y %H:%M"
                ).replace(tzinfo=dtz.gettz("Europe/Kiev")).isoformat()

                timeEnd = datetime.datetime.strptime(  # Converting Schedule timeframe to isoformat
                    f"{ssuEvent['DATE_REG']} {ssuEvent['TIME_PAIR'][6:]}",
                    "%d.%m.%Y %H:%M"
                ).replace(tzinfo=dtz.gettz("Europe/Kiev")).isoformat()

                event = {  # Creating event payload
                    'summary': ssuEvent['NAME_DISC'],
                    'location': ssuEvent['NAME_AUD'] if ssuEvent['NAME_AUD'] else 'Online',
                    'description': f"{ssuEvent['NAME_FIO']}\n{ssuEvent['NAME_STUD']}\n\n{ssuEvent['COMMENT']}",
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
                            {'method': 'popup', 'minutes': user.popup_reminder},
                        ],
                    },
                }

                event = service.events().insert(  # Inserting Events
                    calendarId=calendar_id,
                    body=event
                ).execute()

                logging.debug(f"[{datetime.datetime.now()}]: Event created: {event.get('htmlLink')}")

            service.close()  # closing session, Important!

        except Exception:
            logging.exception(f"[{datetime.datetime.now()}]: Exception occurred!!!")

    logging.info(
        f"[{datetime.datetime.now()}]: Finished updates in {(datetime.datetime.now() - time_start).total_seconds()} seconds."
    )

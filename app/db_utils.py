import logging
import datetime
import requests

from pony.orm import Database, PrimaryKey, Optional, db_session, commit, select

from app.__main__ import CLIENT, URL_DICT, SCOPES, CLIENT_ID, CLIENT_SECRET

db = Database()
db.bind(provider='postgres', user='scheduler', password='scheduler', host='scheduler-db', database='scheduler')


class User(db.Entity):
    email = PrimaryKey(str)
    group_code = Optional(int)
    fetch_days = Optional(int)
    popup_reminder = Optional(int)
    expires_at = Optional(datetime.datetime)
    refresh_token = Optional(str)
    access_token = Optional(str)


db.generate_mapping(create_tables=True)


@db_session
def update_user(email, token_response_payload, group_code=None, fetch_days=None, popup_reminder=None):
    if not User.get(email=email):
        User(
            email=email,
            group_code=group_code if group_code else None,
            fetch_days=fetch_days if fetch_days else None,
            popup_reminder=popup_reminder if popup_reminder else None,
            expires_at=datetime.datetime.now()+datetime.timedelta(seconds=token_response_payload['expires_in']),
            refresh_token=token_response_payload['refresh_token'],
            access_token=token_response_payload['access_token']
        )
    else:
        user = User.get(email=email)
        user.email = email
        user.group_code = group_code if group_code else user.group_code
        user.fetch_days = fetch_days if fetch_days else user.fetch_days
        user.popup_reminder = popup_reminder if popup_reminder else user.popup_reminder
        user.expires_at = datetime.datetime.now()+datetime.timedelta(seconds=token_response_payload['expires_in'])
        user.refresh_token = token_response_payload['refresh_token']
        user.access_token = token_response_payload['access_token']
        commit()


@db_session
def get_access_token(user):
    user = User.get(email=user.email)

    if not user:
        return None

    if user.expires_at < datetime.datetime.now() or (user.expires_at - datetime.datetime.now()).seconds < 10:
        # request a new access token if the old one is expired or about to expire
        try:
            token_url, headers, body = CLIENT.prepare_refresh_token_request(
                URL_DICT['token_gen'],
                refresh_token=user.refresh_token,
                scope=SCOPES
            )

            token_response = requests.post(
                token_url,
                headers=headers,
                data=body,
                auth=(CLIENT_ID, CLIENT_SECRET)
            ).json()
            user.access_token = token_response['access_token']  # update a token in the DB
            commit()

        except:  # Seems like refresh token no longer works
            delete_user(user.email)
            return None

        logging.debug(f"[{datetime.datetime.now()}] Generating a new token for user: {user.email}")

        return token_response['access_token']

    else:
        logging.debug(f"[{datetime.datetime.now()}] Using existing token for user: {user.email}")
        return user.access_token


@db_session
def delete_user(email):
    User[email].delete()
    logging.info(f"[{datetime.datetime.now()}] Deleted user: {email}")


@db_session
def get_users():
    return select(p for p in User)[:2]
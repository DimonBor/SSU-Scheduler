# SSU-Scheduler
Middleware app for pushing schedule from [SSU](https://int.sumdu.edu.ua/en//) to Google Calendar.

## Available params
There are a few params that can be customised.

| Env var          | Default value, units | Notes                                                                                          |
|------------------|----------------------|------------------------------------------------------------------------------------------------|
| `UPDATE_TIMEOUT` | 30, mins             | Events update frequency                                                                        |
| `CLIENT_SECRET`  | None                 | Client Secret from https://console.cloud.google.com/apis/credentials                           |
| `CLIENT_ID`      | None                 | Client ID from https://console.cloud.google.com/apis/credentials                               |
| `WEB_URL`        | None                 | Redirect URL base. External app address which will be used by Google to redirect authorization |

## Basic usage

Deploy the application:
```bash
docker compose up -d
```

Or run dev variant (the only difference is exposed Postres ports):
```bash
docker compose up -d -f docker-compose-dev.yaml
```

Go to web page, complete configuration, and wait till update task will be executed (no longer than `UPDATE_TIMEOUT`)

## Web FAQ

*Q: How to disable scheduler?*

**A: Go to /logout page. This will remove user from app DB and schedule will no longer be updated**

\
*Q: How can I see my current configuration?*

**A: There is no such possibility. All actions are performed with re-authorization with Google. I don't want to write my own authorization system**

\
*Q: Can I set up more than one group to fetch schedule?*

**A: Currently this is not supported, however, maybe will be done in future.**
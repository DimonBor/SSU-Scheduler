# SSU-Scheduler
Middleware for pushing schedule from SSU to Google Calendar

## Available params
There are a few params that can be customised.

|Env var | Default value, units | Notes |
|--------|----------------------|-------|
| `SCHEDULE_PERIOD` | 14, days | For which period in the schedule events will be created |
| `GROUP_CODE` | 1002732, int | Group code for schedule requests |
| `POPUP_REMINDER` | 10, mins | Specify Google Calendar popup reminder |
| `UPDATE_TIMEOUT` | 60, mins | Events update frequency |

## Basic usage
Follow [this](https://developers.google.com/calendar/api/quickstart/python) guide to create your credentials JSON file. Then rename it to `credentials.json` and place in some folder on your machine and run the following command:

```bash
docker run -d --restart=always --net=host -v /path/to/creds/folder/:/creds --name ssu-scheduler dimonbor/ssu-scheduler:latest
```

Check container logs via:
```bash
docker logs ssu-scheduler
```

Here you can find the URL for authorizing the app. Authorize it and on the last step if you start it on the remote machine, copy the URL that fails to access `localhost` and execute it with `curl` on the remote machine. For example:
```bash
curl 'http://localhost:39761/?state=GXrR2BNt3c6KmgTschdojGcRgweJqV&code=4/0AWtgzh7n6iSQtsrrwiqasdAUDxsg540BUMsV4bUMF-qAllQpQjQTSWXwmPmr6kArV6qY2g&scope=https://www.googleapis.com/auth/calendar'
```
Done. Now just wait for the events to be created during the update period.

Running with params:
```bash
docker run -d --restart=always --net=host -v /path/to/creds/folder/:/creds -e UPDATE_TIMEOUT=5 -e SCHEDULE_PERIOD=32 --name ssu-scheduler dimonbor/ssu-scheduler:latest
```
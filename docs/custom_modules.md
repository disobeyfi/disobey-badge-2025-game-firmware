# Windows

Here are our common modules that can be reused.

## Windows

### `LoadingScreen`

This window's purpose is have commong loading screen when loading games.

Note: Currently waiting under 9 seconds (1 digit) has been tested, so longer waiting time might need tuning for the UI

#### Parameters

| Name         | Required | Description                                                                                     |
| ------------ | -------- | ----------------------------------------------------------------------------------------------- |
| `title`      | ✅       | Title to be shown                                                                               |
| `wait`       | ✅       | Time in seconds how long screen is shown                                                        |
| `nxt_scr`    | ✅       | Screen to be loaded after waiting time                                                          |
| `scr_args`   | ❌       | Arguments for the next screen                                                                   |
| `scr_kwargs` | ❌       | Keyword arguments for the next screen. If `scr_args` is provided, value of this will be ignored |

#### Usage

Example with keyword arguments

```python
    Screen.change(LoadingScreen, kwargs={
                  "title": "Title", "wait": 5,
                  "nxt_scr": OTAScreen,
                  "scr_kwargs": {
                      "espnow": e,
                      "sta": sta,
                      "fw_version": Version().version,
                      "ota_config": Config.config["ota"]
                  }
                  })
```

## Widgets

### `HiddenActiveWidget`

Purpose of this widget is to get rid of the default `CloseButton` for screens that we don't want to have it.

#### Parameters

| Name       | Required | Description                |
| ---------- | -------- | -------------------------- |
| `writer`   | ✅       | Writer instance            |
| `callback` | ❌       | Optional callback          |
| `args`     | ❌       | Arguments for the callback |

#### Usage

```
HiddenActiveWidget(self.wri)
```

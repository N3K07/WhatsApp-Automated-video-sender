# WhatsApp Video Sender

A Windows-based WhatsApp video automation tool built with Python and Playwright. It monitors a folder for new video files and sends them to a selected WhatsApp contact through WhatsApp Web. A dashboard provides controls for managing the automation and viewing activity.

## Features

* **Automatic video monitoring:** Watches a designated folder for new video files.
* **WhatsApp Web integration:** Uses Playwright to automate the existing Chrome browser session.
* **Recipient configuration:** Allows you to configure the WhatsApp contact.
* **Dashboard controls:** Start and stop the automation from the dashboard.
* **Activity logs:** View automation activity and troubleshoot errors.
* **File organization:** Moves successfully sent videos into a separate folder.
* **Chrome connection monitoring:** Checks the connection to the Chrome debugging session.

## Technologies Used

* **Python** — application logic and automation control.
* **Playwright** — browser automation.
* **Google Chrome** — runs WhatsApp Web.
* **WhatsApp Web** — interface used to send videos.
* **Windows Batch Scripts** — simplify launching Chrome and the dashboard.

## Requirements

Before getting started, make sure you have:

* Windows 10 or Windows 11
* Python installed
* Google Chrome installed
* A WhatsApp account

## Project Structure

```text
Whatsapp Automation/
├── .gitignore
├── automation_controller.py
├── config.example.json
├── dashboard.py
├── main.py
├── start_chrome.bat
├── start_dashboard.bat
├── whatsapp_sender.py
├── config.json
├── ToSend/
├── Sent/
└── Logs/
```


## Installation


### 1. Install Dependencies

Install Playwright:

```bat
python -m pip install playwright
```

### 2. Configure the Application

Create your local configuration file by copying the example:

```bat
copy config.example.json config.json
```

Open `config.json` in a text editor and update the recipient and other settings using the structure provided in `config.example.json`.

Keep your real configuration file private. Do not upload personal configuration values or browser session data to GitHub.

### 3. Set Up WhatsApp Web

1. Run `start_chrome.bat`.
2. Wait for Chrome to open.
3. Navigate to [WhatsApp Web](https://web.whatsapp.com/) if it does not open automatically.
4. Link your WhatsApp account by scanning the QR code if prompted.
5. Wait until your chats load.

Use the Chrome instance launched by the project so the automation can connect to the correct browser session.

The Chrome debugging port must match the port configured in the project, which is normally `9222`.

## How to Use

### 1. Start Chrome

Run:

```text
start_chrome.bat
```

Keep the Chrome session open and make sure WhatsApp Web is ready.

### 2. Open the Dashboard

Run:

```text
start_dashboard.bat
```

Use the dashboard to configure the recipient, start the automation, stop it when needed, and review activity logs.

### 3. Add Videos

Place the video files you want to send into the `ToSend` folder.

For example:

```text
ToSend/
├── video_one.mp4
├── video_two.mp4
└── video_three.mp4
```

The automation monitors this folder and processes eligible video files.

### 4. Monitor Progress

Check the dashboard and activity logs to see the automation's progress.

Successfully sent files are moved to the `Sent` folder. If a file fails to send, check the logs before trying again.

### 5. Stop the Automation

Use the dashboard's Stop control when you want to stop processing new files.

Avoid closing Chrome while a video is being uploaded or sent.

## Troubleshooting

### Chrome connection fails

* Make sure Chrome was launched using `start_chrome.bat`.
* Check that Chrome is still running.
* Verify that the debugging port matches the project configuration.
* Make sure another Chrome instance has not replaced the expected session.

### WhatsApp Web is not ready

* Open WhatsApp Web in the launched Chrome window.
* Complete QR-code linking if required.
* Wait for chats to finish loading before starting the automation.

### A video does not send

* Check the activity logs for the specific error.
* Confirm that the file is a valid video and can be opened locally.
* Check your internet connection and WhatsApp Web session.
* Confirm whether the video was sent before retrying, to avoid sending duplicates.

### Dependencies are missing

Run the relevant Python installation command again and review any error messages.

## Security and Privacy

* Do not commit `ChromeProfile/`, `config.json`, personal videos, or browser session data.
* Keep local logs and recipient information private.
* Use a private repository if the source code should not be publicly accessible.
* Respect WhatsApp's terms, recipient consent, and applicable messaging rules.

## Limitations

This project relies on WhatsApp Web and Chrome, so changes to WhatsApp's interface or browser behavior may require updates to the automation. Successful sending depends on a working browser session, network connectivity, and valid video files.

## Disclaimer

It is not affiliated with, endorsed by, or officially supported by WhatsApp or Meta.

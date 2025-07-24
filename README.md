# NetConfParser
NetConfParser is a graphic tool displaying NETConf exchanges between a Netconf Server and a NetConf Client

![NetConfParser](doc/netconfparser.png)

It is also able to provide a quick analysis if the logs are coming from O-RAn Fronthaul protocol

![ORAN Analysis](doc/oran_analysis.png)

## Log Format Support
The input for NetConfParser is a log file containing all messages exchanged.
NetConfParser handles multiple types of Log File:



<details>
  <summary>plain xml</summary>

![Plain XML Log](doc/plain_xml.png)

</details>

<details>
  <summary>netopeer2-server format</summary>

![Netopeer2-server log](doc/netopeer2_server.png)

</details>

## Parsing log file
NetConfParser supports drag and drop.
NetConfParser supports unpacking .xz files directly.

![Drag And Drop](doc/drag_and_drop.gif)


If the log file is heavy (multiple MBs), a progress bar appears on the right side.

![Progress Bar](doc/progress_bar.gif)

Some RPC Replies may be very heavy and result in NetConfParser taking several seconds to display the whole data.
If you want to speed up the performance, you can uncheck the box `Parse Enormous RPCs` (default behaviour)

## Messages Display
### Main Window
After parsing your log file, the different exchanges will appear in the main frame.
Messages are displayed in the following categories:
- hello
- rpc get-schema
- rpc get
- rpc
- rpc-reply
- notification netconf-config-change
- notification

![Categories](doc/netconfparser.png)

A small summary of the contents of the message is available in the `data` cell.

When a rpc is not answered, it is displayed in orange.
If the rpc-reply contains an rpc-error, it is displayed in red.

Full contents of each message can be displayed by clicking on the `+` sign:

![Expand](doc/expand.gif)

### Searching for elements
You can use the `search` Text Box to display only elements of the tree that contain certain keywords.
Then click on `Filter` button to display
Regex syntax is supported (case is ignored)
To clear your search and go back to the full tree, click on `Clear Search` button
`Clear Tree` will clear the whole window.
If you selected an item before clicking on `Clear Search`, then tree will focus back on this element.

### Copy Messages
Upon selecting a message, a formatted version of this message is displayed in the box on the right side:

![CopyToClipBoard](doc/copy_to_clipboard.gif)

You can then use the button `Copy To Clipboard` to copy it.

## ORAN Analysis
By clicking on the right button `See ORAN Analysis`, the view switches from message display to
steps for Radio Configuration.

![ORAN Analysis](doc/oran_analysis.png)

Steps supported:
- Netconf Client Connection
- Supported O-RAN MPlane version display
- Hardware Detection
- Module Capabilities
- User Plane Configuration
- Creation/Deletion of Low Level Endpoints
- Creation of Low Level Links
- Creation/Activation/Deactivation/Deletion of Array Carriers
- Reporting of State BUSY/READY of Array Carriers

Also Failures are displayed
- Rpc Errors

In each of the steps a small summary of objects can be displayed by clicking on the `+` sign:

![ORAN Analysis expand](doc/expand_analysis.gif)

## Availability for Windows
NetConfparser zipfile is available in the [Releases tab](https://github.com/AeroFlorian/netconf-parser/releases)
Unzip it and launch NetConfParser.exe

## Building NetConfParser locally

### Build the project

> [!NOTE]
> Tested using python 3.12 / python 3.13

In a git bash terminal (can use mingw on windows for instance), Generate venv folder using:

```markdown
python -m venv venv
```

Activate it (Next time you can just run this to set the env for your shell)

```markdown
source venv\Scripts\activate
```

At this point you should see (venv) before your PS1.

Install requirements
```markdown
python -m pip install -r requirements.txt
```

#### Note about Proxy when installing requirements

If you are behind a proxy, ensure that your proxy settings are correctly configured. You can set the `HTTP_PROXY` and `HTTPS_PROXY` environment variables before installing the requirements:

```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
```
Replace `your-proxy` and `port` with your proxy details.

For instance **export https_proxy='135.245.192.7:8000'**

### Run the app

```bash
python src/netconfparser.py
```

### Generate the release package

NetConfParser can be built for Windows with pyinstaller
*  pyinstaller --windowed --icon=fs.ico -F --onefile src/netconfparser.py --additional-hooks-dir=. --add-data "fs.ico;."

* If spec file is already generated, you can also use **pyinstaller src/netconfparser.spec**

* It will give an exe as output in dist folder
Please zip it if you want to distribute it
For Linux, you can use python netconfparser.py directly

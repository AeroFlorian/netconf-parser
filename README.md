# Building NetConfParser
NetConfParser can be built for Windows with pyinstaller
        pyinstaller  --windowed --icon=fs.ico netconfparser.py --add-data "fs_ico_encoded;."
It will give an exe as output in dist folder
Please zip it if you want to distribute it
For Linux, you can use python netconfparser.py directly

# Using NetConfParser
Usage of NetConfParser is pretty straightforward

# Loading log file
You can either paste the entire content of the log file in the upper right text box
Or use the load button which will open a dialog box

# Parsing log file
After loading the log file, you will have it pasted in the upper right text box
Just press the Paste button just under the text box
A tree will appear on the left frame

# Reading the output tree
Output tree is on the left frame
In yellow you have the hello and the notifications
In blue the rpcs coming from ODU
In green the rpc responses coming from ORU
You can expand the content of all messages by clicking the + on the left

# Generating SCT file to reproduce PRs -- Not usable
Under the lower right text box press the button Generate SCT
Text will appear in the lower right text box
Use then Copy To Clipboard button to copy


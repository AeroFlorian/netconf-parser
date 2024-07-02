import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD

import time
from Logger import logger
import traceback
import re
import xmltodict
import uuid
import textwrap
import uu

text_box = None
result_box = None
sct_box = None
lines = []
detached_items = []
items = []
received_rpcs = []
message_id_without_counterpart = []


def wrap(string, length=100):
    return '\n'.join(textwrap.wrap(string, length))


def json_tree(parent, dictionary, tags, depth=0):
    for key in dictionary:
        uid = uuid.uuid4()
        if isinstance(dictionary[key], dict):
            result_box.insert(parent, 'end', uid, text='', values=(
                "", "", "", "\t" * depth + key, ""), tags=tags)
            json_tree(uid, dictionary[key], tags, depth + 1)
        elif isinstance(dictionary[key], list):
            json_tree(parent,
                      dict([(key + (" " * i), x) for i, x in enumerate(dictionary[key])]), tags, depth + 1)
        else:
            value = dictionary[key]
            key_without_ns = key.split(':')[-1]
            if value is None:
                value = ""
            vl = value.split("\n")
            vl_wrapped = []
            for v in vl:
                for x in textwrap.wrap(v, 100):
                    vl_wrapped.append(x)
            vl = vl_wrapped
            if len(vl) > 1:
                for i, v in enumerate(vl):
                    uid = uuid.uuid4()
                    result_box.insert(parent, 'end', uid, text='', values=(
                        "", "", "", "\t" * depth + str(key_without_ns) if i == 0 else "", wrap(v)), tags=tags)
            else:
                result_box.insert(parent, 'end', uid, text='', values=(
                "", "", "", "\t" * depth + str(key_without_ns), wrap(value)), tags=tags)


def parse_file(full_lines):
    global message_id_without_counterpart
    reg = r'<rpc .*? message-id=.(\d+).>(.*?)</rpc>|' \
          r'<rpc-reply .*? message-id=.(\d+).>(.*?)</rpc-reply>|' \
          r'<notification xmlns=\".*?\">.*eventTime>(.*?)</notification>|'\
          r'<hello xmlns=\".*?\">(.*?)</hello>'

    all_matches = re.findall(reg, full_lines, re.MULTILINE|re.DOTALL)
    hello_req = False
    for i,element in enumerate(all_matches):
        #Hello case
        if element[5] != "":
            data = element[5]
            message_type = "hello"
            message_id = "0"
            data = element[5]
            d = "->" if not hello_req else "<-"
            tags = "hello"
            hello_req = not hello_req
            data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)
            data = re.sub(r'<session-id.*/session-id>', '', data)
        elif element[0] != "": #rpc case
            message_type = "rpc"
            message_id = element[0]
            data = element[1]
            d = "->"
            tags = "req"
            if "get-schema" not in data:
                message_id_without_counterpart.append(int(message_id))
            else:
                message_type = "get-schema"
                tags = "schema"
            data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)

        elif element[2] != "": #rpc-reply case

            message_type = "rpc-reply"
            message_id = element[2]
            data = element[3]
            d = "<-"
            if "rpc-error" in data:
                tags = "rpc-error"
            else:
                tags = "resp"
            if int(message_id) in message_id_without_counterpart:
                message_id_without_counterpart.remove(int(message_id))
            data = re.sub(r' [^ ]+=\"[^\"]+\"', '', data)
            data = re.sub(r'^.*?<', '<', data, flags=re.DOTALL)
            data = re.sub(r'>[^>]*?$', '>', data, flags=re.DOTALL)
            data = re.sub(r'} {', '', data, flags=re.DOTALL)
        elif element[4] != "": #notification case
            message_type = "notification"
            message_id = "0"
            data = element[4]
            d = "<-"
            tags = "notification"
            data = re.sub(r' xmlns[^ ]*=\"[^\"]+\"', '', data)

        try:
            dic = xmltodict.parse(data)
        except Exception as e:
            dic = {"": f"Failed to parse data: {e}"}
        parent = result_box.insert('', 'end', text='', values=(
            message_id, d, message_type, "", ""), tags=tags)
        json_tree(parent, dic, tags)


def search_in_element(query, element):
    if query.lower() in str(result_box.item(element)['values'][2]) or query.lower() in str(
            result_box.item(element)['values'][3]) or query.lower() in str(result_box.item(element)['values'][4]):
        return True
    result = False
    for child in result_box.get_children(element):
        result = result or search_in_element(query, child)
    return result


def search(event):
    query = filter_text.get()
    selections = []
    for child in result_box.get_children():
        if not search_in_element(query, child):
            selections.append(child)
            detached_items.append(child)
        items.append(child)
    for item in selections:
        result_box.detach(item)


def clear_search(event):
    for (index, i) in enumerate(items):
        if i in detached_items:
            result_box.reattach(i, '', index)
    detached_items.clear()
    items.clear()


def clear_tree(event):
    if len(items) == 0:
        for child in result_box.get_children():
            items.append(child)
    for item in items:
        result_box.delete(item)
    items.clear()
    detached_items.clear()
    message_id_without_counterpart.clear()


def get_text_box(event):
    result_box.delete(*result_box.get_children())
    full = text_box.get("1.0", tk.END)
    text_box.delete("1.0", tk.END)
    parse_file(full)
    # Apply no counterparts tag
    for child in result_box.get_children():
        if result_box.item(child)['values'][0] != "N/A" and int(
                result_box.item(child)['values'][0]) in message_id_without_counterpart:
            result_box.item(child, tags=['no-counterpart'])
    result_box.tag_configure("hello", background='lightyellow')
    result_box.tag_configure("req", background='lightblue')
    result_box.tag_configure("schema", background='#70c38e')
    result_box.tag_configure("resp", background='lightgreen')
    result_box.tag_configure("notif", background='lightyellow')
    result_box.tag_configure("rpc-error", background='red')
    result_box.tag_configure("no-counterpart", background='orange')


def load_file(event):
    f = filedialog.askopenfile()
    text_box.insert('1.0', f.readlines())


def copy_to_clipboard(event):
    window.clipboard_clear()
    full = sct_box.get("1.0", tk.END)
    window.clipboard_append(full)
    window.update()

def open_children(parent):
    result_box.item(parent, open=True)
    for child in result_box.get_children(parent):
        open_children(child)

def handleOpenEvent(event):
    open_children(result_box.focus())

def update_title(file):
    window.title(f"NetConfParser - {file}")

def load_file(file):
    clear_tree(None)
    text_box.delete('1.0', tk.END)
    logger.info(f"Loading file: {file.data}")
    with open(file.data, 'r') as f:
        text_box.insert('1.0', f.readlines())
    get_text_box(None)
    update_title(file.data)


if __name__ == "__main__":

    try:
        uu.decode('fs_ico_encoded', 'fs.ico')
        window = TkinterDnD.Tk()
        s = ttk.Style()


        # workaround for row coloring
        # if window.getvar('tk_patchLevel') == '8.6.9':
        def fixed_map(option):
            return [elm for elm in s.map('Treeview', query_opt=option) if elm[:2] != ('!disabled', '!selected')]


        s.map('Treeview', foreground=fixed_map('foreground'),
              background=fixed_map('background'))
        # end workaround
        window.title('NetConfParser')
        window.wm_iconbitmap('fs.ico')
        window.iconbitmap('fs.ico')
        window.state('zoomed')
        frame_l = tk.Frame(width=200, height=400)
        frame_r = tk.Frame(width=100, height=200)

        label = tk.Label(master=frame_r, text="Paste log here")
        text_box = tk.Text(master=frame_r)
        sct_box = tk.Text(master=frame_r)
        copy_sct = tk.Button(master=frame_r, text="Copy to clipboard")
        filter_text = tk.Entry(master=frame_l)
        filter_button = tk.Button(master=frame_l, text="Filter")
        clear_button = tk.Button(master=frame_l, text="Clear Search")
        clear_tree_button = tk.Button(master=frame_l, text="Clear Tree")

        result_box = ttk.Treeview(master=frame_l)
        result_box["columns"] = ("id", "direction", "type", "data", "data2")
        result_box.column("#0", width=150, minwidth=10, stretch=tk.NO)
        result_box.column("id", width=50, minwidth=20,
                          stretch=tk.NO, anchor="c")
        result_box.column("direction", width=50, minwidth=100,
                          stretch=tk.NO, anchor="c")
        result_box.column("type", width=100, minwidth=100,
                          stretch=tk.NO, anchor="c")
        result_box.column("data", width=400, minwidth=400)
        result_box.column("data2", width=200, minwidth=200)
        result_box.heading('#0', text='', anchor=tk.CENTER)
        result_box.heading('id', text='id', anchor=tk.CENTER)
        result_box.heading('direction', text='dir', anchor=tk.CENTER)
        result_box.heading('type', text='type', anchor=tk.CENTER)
        result_box.heading('data', text='data', anchor=tk.CENTER)
        result_box.heading('data2', text='', anchor=tk.CENTER)

        result_box.bind('<<TreeviewOpen>>', handleOpenEvent)

        sb = tk.Scrollbar(frame_l, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb2 = tk.Scrollbar(frame_l, orient=tk.HORIZONTAL)
        sb2.pack(side=tk.BOTTOM, fill=tk.X)

        result_box.config(xscrollcommand=sb2.set)
        result_box.config(yscrollcommand=sb.set)
        sb.config(command=result_box.yview)
        sb2.config(command=result_box.xview)

        parse_button = tk.Button(master=frame_r, text="Parse")
        load_button = tk.Button(master=frame_r, text="Load File")

        filter_text.place(y=20, x=50, width=400)
        filter_button.bind("<Button-1>", search)
        filter_button.place(y=20, x=500, width=200)
        clear_button.bind("<Button-1>", clear_search)
        clear_button.place(y=20, x=710, width=200)
        clear_tree_button.bind("<Button-1>", clear_tree)
        clear_tree_button.place(y=20, x=920, width=200)
        label.place(y=10, relx=.5, anchor="center")
        text_box.place(x=10, y=20, width=80, height=200)

        text_box.drop_target_register(DND_FILES)
        text_box.dnd_bind('<<Drop>>', load_file)
        result_box.drop_target_register(DND_FILES)
        result_box.dnd_bind('<<Drop>>', load_file)

        result_box.place(y=50, relwidth=1.0, relheight=0.95)
        parse_button.bind("<Button-1>", get_text_box)
        parse_button.place(y=240, relx=.5, anchor="center")
        load_button.bind("<Button-1>", load_file)
        load_button.place(y=280, relx=.5, anchor="center")
        sct_box.place(x=10, y=300, width=80, height=200)
        copy_sct.place(y=560, relx=.5, anchor="center")
        copy_sct.bind("<Button-1>", copy_to_clipboard)

        frame_l.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        frame_r.pack(fill=tk.Y, side=tk.RIGHT)
        window.mainloop()
    except Exception as e:
        logger.error("Exception Caught!")
        for l in traceback.format_exc().splitlines():
            logger.error(l)

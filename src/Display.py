import tkinter as tk
# import ttkbootstrap as ttk
from tkinter import ttk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import OranMessageDefs
import NetconfMessageDefs
import MessageParser
import textwrap
import uuid
import re
import threading
import xml.dom.minidom
from Logger import logger
import os
import lzma
import webbrowser
from version import __version__
import Utils
import Constants
import UpdateChecker

APP_NAME = f"NetConfParser - {__version__}{ ' - DEV' if Utils.is_dev_mode() else ''}"
ENORMOUS_RPC=20000

ICON_PATH = os.path.join(os.path.dirname(__file__), 'fs.ico')

def wrap(string, length=100):
    return '\n'.join(textwrap.wrap(string, length))


def json_tree(parent, dictionary, tags, depth=0, box=None, xml=""):
    for key in dictionary:
        uid = uuid.uuid4()
        if isinstance(dictionary[key], dict):
            box.insert(parent, 'end', uid, text='', values=(
                "", "", "", "", "\t" * depth + key, "", xml), tags=tags)
            json_tree(uid, dictionary[key], tags, depth + 1, box=box, xml=xml)
        elif isinstance(dictionary[key], list):
            json_tree(parent,
                      dict([(key + (" " * i), x) for i, x in enumerate(dictionary[key])]), tags, depth + 1, box=box,
                      xml=xml)
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
                    box.insert(parent, 'end', uid, text='', values=(
                        "", "", "", "", "\t" * depth + str(key_without_ns) if i == 0 else "", wrap(v), xml), tags=tags)
            else:
                box.insert(parent, 'end', uid, text='', values=(
                    "", "", "", "", "\t" * depth + str(key_without_ns), wrap(value), xml), tags=tags)


def open_children(parent, box):
    box.item(parent, open=True)
    for child in box.get_children(parent):
        open_children(child, box)


def handleOpenEvent(event, box):
    open_children(box.focus(), box)


def pretty_print_xml(xml_str: str):
    if not str:
        return str
    st = xml.dom.minidom.parseString(xml_str)
    pps = st.toprettyxml(indent='    ')
    pps = re.sub(r'<.xml version="1.0" .>\n', "", pps)
    return pps

class BaseTreeview(ttk.Treeview):
    """
    Base class to extend tree view with right click menu feature, to easily copy its content to the clipboard
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_cell_content)

        # Bind right-click to show the context menu
        self.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Display the context menu at the cursor position."""
        item = self.identify_row(event.y)
        if item:
            self.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def get_cell_content(self):
        selected_item = self.selection()
        if selected_item:
            item_values = self.item(selected_item[0], "values")
            column = self.identify_column(self.winfo_pointerx() - self.winfo_rootx())
            column_index = int(column[1:]) - 1  # Convert column ID (e.g., "#1") to index
            if 0 <= column_index < len(item_values):
                return item_values[column_index]
        return None

    def copy_cell_content(self):
        cell_value = self.get_cell_content()
        if cell_value:
            self.clipboard_clear()
            self.clipboard_append(cell_value)
            self.update()


class ResultBox(BaseTreeview):
    def __init__(self, frame: tk.Frame, text_box: tk.Text, filter_text: tk.Entry, parse_enormous_rpc: tk.IntVar, pb: ttk.Progressbar, label: tk.Label):
        super().__init__(master=frame, columns=("timestamp", "id", "direction", "type", "data", "data2", "xml"),
                         displaycolumns=("timestamp", "id", "direction", "type", "data", "data2"))
        self.column("#0", width=50, minwidth=10, stretch=tk.NO)
        self.column("timestamp", width=150, minwidth=10, stretch=tk.NO, anchor=tk.CENTER)
        self.column("id", width=50, minwidth=20, stretch=tk.NO, anchor="c")
        self.column("direction", width=50, minwidth=100, stretch=tk.NO, anchor="c")
        self.column("type", width=100, minwidth=100, stretch=tk.NO, anchor="c")
        self.column("data", width=400, minwidth=400)
        self.column("data2", width=200, minwidth=200)
        self.heading('#0', text='', anchor=tk.CENTER)
        self.heading('timestamp', text='timestamp', anchor=tk.CENTER)
        self.heading('id', text='id', anchor=tk.CENTER)
        self.heading('direction', text='dir', anchor=tk.CENTER)
        self.heading('type', text='type', anchor=tk.CENTER)
        self.heading('data', text='data', anchor=tk.CENTER)
        self.heading('data2', text='', anchor=tk.CENTER)
        self.messages: list = []
        self.bind('<<TreeviewOpen>>', lambda x: handleOpenEvent(x, self))
        self.text_box = text_box
        self.filter_text = filter_text
        self.parse_enormous_rpc = parse_enormous_rpc
        self.bind("<Button-1>", self.show_message_in_text)
        self.saved_items_for_search = []
        self.detached_items = []
        self.filter_text.bind("<Return>", self.search)
        self.pb = pb
        self.label = label

        # only available for result box
        self.context_menu.add_command(label="Search", command=self.search_cell_content)

    def add_messages(self, messages: list[NetconfMessageDefs.Message]):
        self.pb.pack(fill=tk.Y, pady=30)
        self.label.pack(anchor='center')
        self.messages = messages
        for index,message in enumerate(messages):
            self.pb["value"] = int(index/len(messages)*100)
            self.label["text"] = f"   {int(index/len(messages)*100)}%\n{index+1}/{len(messages)}"
            if len(message.raw_data) < ENORMOUS_RPC or self.parse_enormous_rpc.get() == 1:
                parent = self.insert("", tk.END, values=message.get_values(), tags=message.tag.name.lower())
                json_tree(parent, message.data, message.tag.name.lower(), box=self, xml=message.raw_data)
            else:
                values = list(message.get_values())
                values[3] = "\t\t\tData too large to display"
                parent = self.insert("", tk.END, values=tuple(values), tags=message.tag.name.lower())
        self.pb.pack_forget()
        self.label.pack_forget()

    def show_message_in_text(self, event):
        item = self.identify('item', event.x, event.y)
        if item:
            item = self.item(item)
            if item['values']:
                self.text_box.delete(1.0, tk.END)
                self.text_box.insert(tk.END, pretty_print_xml(item['values'][6]))

    def clear_all(self):
        self.delete(*self.get_children())
        self.messages = []

    def apply_tags(self):
        self.tag_configure("hello", background='lightyellow')
        self.tag_configure("rpc", background='lightblue')
        self.tag_configure("schema", background='#70c38e')
        self.tag_configure("rpc_reply", background='lightgreen')
        self.tag_configure("notification", background='#faebd7')
        self.tag_configure("notification_netconf_config_change", background='#cd9575')
        self.tag_configure("rpc_error", background='#ff6242')
        self.tag_configure("rpc_without_counterpart", background='orange')

    def search_in_element(self,query, element):
        return re.search(query, str(self.item(element)['values'][6]), re.IGNORECASE) is not None

    def search(self, event):
        self.clear_search(event)
        query = self.filter_text.get()
        selections = []
        for child in self.get_children():
            if not self.search_in_element(query, child):
                selections.append(child)
                self.detached_items.append(child)
            self.saved_items_for_search.append(child)
        for item in selections:
            self.detach(item)

    def clear_search(self, event):
        selected_item = self.selection()
        for (index, i) in enumerate(self.saved_items_for_search):
            if i in self.detached_items:
                self.reattach(i, '', index)
        self.detached_items.clear()
        self.saved_items_for_search.clear()
        if selected_item:
            self.see(selected_item)

    def search_cell_content(self):
        """Search based on the content of the selected cell."""
        cell_value = self.get_cell_content()
        if cell_value:
            self.perform_search(cell_value)

    def perform_search(self, query):
        self.filter_text.delete(0, tk.END)
        self.filter_text.insert(0, query)
        self.clear_search(None)
        self.search(None)

class AnalysisBox(BaseTreeview):
    def __init__(self, frame: tk.Frame, text_box: tk.Text):
        super().__init__(master=frame, columns=("timestamp", "msg-id", "category", "status", "information", "data2"))
        self.column("#0", width=25, minwidth=10, stretch=tk.NO)
        self.column("timestamp", width=25, minwidth=10, stretch=tk.NO, anchor=tk.CENTER)
        self.column("msg-id", width=50, minwidth=20, stretch=tk.NO, anchor="c")
        self.column("category", width=100, minwidth=100, stretch=tk.NO, anchor="c")
        self.column("status", width=50, minwidth=100, stretch=tk.NO, anchor="c")
        self.column("information", width=200, minwidth=200)
        self.column("data2", width=200, minwidth=200)
        self.heading('#0', text='', anchor=tk.CENTER)
        self.heading('timestamp', text='', anchor=tk.CENTER)
        self.heading('msg-id', text='msg-id', anchor=tk.CENTER)
        self.heading('category', text='category', anchor=tk.CENTER)
        self.heading('status', text='status', anchor=tk.CENTER)
        self.heading('information', text='information', anchor=tk.CENTER)
        self.heading('data2', text='', anchor=tk.CENTER)
        self.bind('<<TreeviewOpen>>', lambda x: handleOpenEvent(x, self))
        self.bind("<Button-1>", self.show_message_in_text)
        self.text_box = text_box
        self.messages = []

    def add_messages(self, messages: list[OranMessageDefs.OranMessage]):
        self.messages = messages
        for message in messages:
            parent = self.insert("", tk.END, values=message.get_values(), tags=message.category.replace(" ", "_"))
            if message.data_to_display:
                json_tree(parent, message.data_to_display, message.category, box=self, xml=message.raw_data)

    def show_message_in_text(self, event):
        item = self.identify('item', event.x, event.y)
        if item:
            item = self.item(item)
            if item['values']:
                self.text_box.delete(1.0, tk.END)
                self.text_box.insert(tk.END, pretty_print_xml(item['values'][6]))

    def clear_all(self):
        self.delete(*self.get_children())
        self.messages = []

    def apply_tags(self):
        self.tag_configure("RU", background='lightgreen')
        self.tag_configure("ERR", background='#ff6242')
        self.tag_configure("WRN", background='#e89149')
        background_cells = [
            "#32cd32",
            "#93dc5c",
            "#b7e892",
            "#dbf3c9",
            "#c3f550"
        ]
        tag_cells_found = set()
        for message in self.messages:
            if message.category.startswith("Cell"):
                tag_cells_found.add(message.category.replace(" ", "_"))
        for index, tag_cell in enumerate(tag_cells_found):
            self.tag_configure(f"{tag_cell}", background=background_cells[index % 5])


class NetConfParserWindow(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.netconf_parser = None
        self.title(APP_NAME)
        try:
            self.wm_iconbitmap(ICON_PATH)
            self.iconbitmap(ICON_PATH)
        except:
            pass
        self.state('zoomed')

        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        export_menu = tk.Menu(self.menu_bar, tearoff=0)
        export_menu.add_command(label="Export RPCs to file", command=self.export_rpcs)
        self.menu_bar.add_cascade(label="Export", menu=export_menu)

        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about_popup)
        help_menu.add_command(label="Check for Update", command=self.check_for_update)
        self.menu_bar.add_cascade(label="?", menu=help_menu)

        frame_l = tk.Frame(width=200, height=400)
        frame_r = tk.Frame(width=100, height=200)

        oran_analysis = tk.Button(master=frame_r, text="See ORAN Analysis")
        back_to_tree = tk.Button(master=frame_r, text="Back to Tree")
        parse_enormous_rpc = tk.IntVar()
        parse_snapshot = tk.Checkbutton(master=frame_r, text='Parse Enormous RPCs', variable=parse_enormous_rpc,
                                        onvalue=1, offvalue=0)
        self.filter_text = tk.Entry(master=frame_l)
        self.filter_button = tk.Button(master=frame_l, text="Filter")
        self.clear_button = tk.Button(master=frame_l, text="Clear Search")
        clear_tree_button = tk.Button(master=frame_l, text="Clear Tree")

        message_text_box = tk.Text(master=frame_r, width=20, height=20)
        pb = ttk.Progressbar(frame_r, orient='vertical', mode='determinate', length=280)
        label_pb = ttk.Label(frame_r, text="0%")

        result_box = ResultBox(frame_l, message_text_box, self.filter_text, parse_enormous_rpc, pb, label_pb)

        copy_to_clip = tk.Button(master=frame_r, text="Copy To Clipboard")

        sb = tk.Scrollbar(frame_l, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb2 = tk.Scrollbar(frame_l, orient=tk.HORIZONTAL)
        sb2.pack(side=tk.BOTTOM, fill=tk.X)

        result_box.config(xscrollcommand=sb2.set)
        result_box.config(yscrollcommand=sb.set)
        sb.config(command=result_box.yview)
        sb2.config(command=result_box.xview)

        load_button = tk.Button(master=frame_r, text="Load File")

        analysis_box = AnalysisBox(frame_l, message_text_box)

        self.filter_text.place(y=20, x=50, width=400)
        self.filter_button.bind("<Button-1>", result_box.search)
        self.filter_button.place(y=20, x=500, width=200)
        self.clear_button.bind("<Button-1>", result_box.clear_search)
        self.clear_button.place(y=20, x=710, width=200)
        clear_tree_button.bind("<Button-1>", self.clear_tree)
        clear_tree_button.place(y=20, x=920, width=200)
        result_box.drop_target_register(DND_FILES)
        analysis_box.drop_target_register(DND_FILES)

        result_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)


        label_pb.pack_forget()
        analysis_box.pack_forget()

        load_button.pack(anchor="center", pady=20)
        load_button.bind("<Button-1>", self.open_dialog_and_load_file)
        parse_snapshot.pack(anchor="center", after=load_button)
        message_text_box.pack(anchor="center", after=parse_snapshot)
        copy_to_clip.pack(anchor="center", after=message_text_box)
        oran_analysis.pack(anchor="center", after=copy_to_clip)

        # back_to_tree.place(y=560, relx=.5, anchor="center")
        back_to_tree.pack_forget()

        back_to_tree.bind("<Button-1>", self.back_to_tree_view)
        oran_analysis.bind("<Button-1>", self.launch_oran_analysis)
        copy_to_clip.bind("<Button-1>", self.copy_to_clipboard)
        pb.pack_forget()

        frame_l.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)
        frame_r.grid_propagate(False)
        frame_r.pack(fill=tk.Y, side=tk.RIGHT)

        self.s = ttk.Style()

        # workaround for row coloring
        def fixed_map(option):
            return [elm for elm in self.s.map('Treeview', query_opt=option) if elm[:2] != ('!disabled', '!selected')]

        self.s.map('Treeview', foreground=fixed_map('foreground'),
              background=fixed_map('background'))

        self.result_box = result_box
        self.analysis_box = analysis_box
        self.message_text_box = message_text_box
        self.sb = sb
        self.sb2 = sb2
        self.back_to_tree = back_to_tree
        self.oran_analysis = oran_analysis
        self.copy_to_clip = copy_to_clip

        self.enable_drop_for_result_box() # Only the visible box should have the drag & drop
        self.check_for_update()

    def check_for_update(self):
        threading.Thread(target=UpdateChecker.check_for_updates, daemon=True).start()

    def open_dialog_and_load_file(self, event):
        f = filedialog.askopenfile()
        if f:
            self.load_and_parse_file(f.name)

    def enable_drop_for_result_box(self):
        self.result_box.dnd_bind('<<Drop>>', self.load_file)
        self.analysis_box.unbind('<<Drop>>')

    def enable_drop_for_analysis_box(self):
        self.analysis_box.dnd_bind('<<Drop>>', self.load_file)
        self.result_box.unbind('<<Drop>>')

    def extract_xz_file(self, file_path, output_path):
        try:
            with lzma.open(file_path) as xz_file:
                with open(output_path, 'wb') as out_file:
                    out_file.write(xz_file.read())
            logger.info(f"Extracted {file_path} to {output_path}")
        except Exception as e:
            logger.error(f"Failed to extract {file_path}: {e}")

    def is_xz_file(self, file_path):
        return file_path.lower().endswith('.xz')

    def handle_xz_file(self, file_path):
        if self.is_xz_file(file_path):
            output_path = os.path.splitext(file_path)[0]  # Remove .xz extension
            self.extract_xz_file(file_path, output_path)
            return output_path
        return file_path

    def load_file(self, event):
        try:
            file = event.data.strip("{}")  # Remove curly braces if present
            if self.is_xz_file(file):
                file = self.handle_xz_file(file)
            self.load_and_parse_file(file)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to handle file: {e}")

    def threaded_operation(self, netconf_parser):
        self.result_box.add_messages(netconf_parser.get_netconf_messages())
        self.result_box.apply_tags()
        self.analysis_box.add_messages(netconf_parser.get_oran_messages())
        self.analysis_box.apply_tags()
        self.back_to_tree_view(None)
        self['cursor'] = 'arrow'

    def load_and_parse_file(self, file):
        self['cursor'] = 'watch'
        self.result_box.clear_all()
        self.analysis_box.clear_all()
        self.pack_forget_boxes()

        # try:
        file_name = re.sub(r"{", "", file)
        file_name = re.sub(r"}", "", file_name)
        self.title(f"{APP_NAME} - {file_name}")
        with open(file_name, 'r') as f:
            data = '\n'.join(f.readlines())
            netconf_parser = MessageParser.NetConfParser(data)
            netconf_parser.parse()
            netconf_messages = netconf_parser.get_netconf_messages()
            t1 = threading.Thread(target=self.threaded_operation, args=(netconf_parser,))
            t1.start()

        # except:
        #     tk.messagebox.showerror("Error", f"Cannot open file {file_name}")
        #     return

    def pack_forget_boxes(self):
        self.result_box.pack_forget()
        self.analysis_box.pack_forget()

    def update_search_buttons(self, enable: bool):
        """In Oran analysis, search is not implemented so grey out these buttons & fields"""
        state = "normal" if enable else "disabled"
        self.filter_text.config(state=state)
        self.filter_button.config(state=state)
        self.clear_button.config(state=state)

    def launch_oran_analysis(self, event):
        self.back_to_tree.pack()
        self.oran_analysis.pack_forget()
        self.result_box.pack_forget()
        self.analysis_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
        self.analysis_box.config(xscrollcommand=self.sb2.set)
        self.analysis_box.config(yscrollcommand=self.sb.set)
        self.sb.config(command=self.analysis_box.yview)
        self.sb2.config(command=self.analysis_box.xview)

        self.update_search_buttons(enable=False)
        self.enable_drop_for_analysis_box()

    def back_to_tree_view(self, event):
        self.back_to_tree.pack_forget()
        self.oran_analysis.pack()
        self.analysis_box.pack_forget()
        self.result_box.pack(anchor="center", expand=True, fill=tk.BOTH, pady=60)
        self.result_box.config(xscrollcommand=self.sb2.set)
        self.result_box.config(yscrollcommand=self.sb.set)
        self.sb.config(command=self.result_box.yview)
        self.sb2.config(command=self.result_box.xview)

        self.update_search_buttons(enable=True)
        self.enable_drop_for_result_box()

    def copy_to_clipboard(self, event):
        self.clipboard_clear()
        full = self.message_text_box.get("1.0", tk.END)
        self.clipboard_append(full)
        self.update()

    def clear_tree(self, event):
        self.result_box.clear_all()
        self.analysis_box.clear_all()

    def show_about_popup(self):
        """Display the About popup with app details."""
        popup = tk.Toplevel(self)
        popup.title("About NetConfParser")
        popup.geometry("300x200")
        popup.resizable(False, False)
        popup.transient(self)  # Make the popup a child of the main window
        popup.grab_set()  # Freeze the popup inside the main window


        # Add the app icon
        try:
            popup.iconbitmap(ICON_PATH)
        except Exception as e:
            print(f"Failed to set popup icon: {e}")

        # Add app name
        app_name_label = tk.Label(popup, text=APP_NAME, font=("Arial", 14, "bold"))
        app_name_label.pack(pady=10)

        # Add description
        description = (
            "NetConfParser is a tool designed to parse and analyze Netconf messages.\n"
            "It provides a user-friendly interface to explore each message details."
        )
        description_label = tk.Label(popup, text=description, wraplength=280, justify="center")
        description_label.pack(pady=10)

        def open_github():
            webbrowser.open(Constants.GITHUB_REPO_URL)

        github_link = tk.Label(popup, text="GitHub Repository", fg="blue", cursor="hand2")
        github_link.pack(pady=10)
        github_link.bind("<Button-1>", lambda e: open_github())
        self.center_popup(popup, 300, 200)

    def export_rpcs(self):
        if not self.result_box.messages:
            tk.messagebox.showwarning("No Messages", "No parsed messages available to export. Did you parse a file first ?")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return  # User canceled the file dialog

        direction_popup = tk.Toplevel(self)
        direction_popup.title("Select Export Direction")
        direction_popup.iconbitmap(ICON_PATH)
        direction_popup.resizable(False, False)
        direction_popup.transient(self)  # Make the popup a child of the main window
        direction_popup.grab_set()  # Freeze the popup inside the main window

        # Popup dimension configuration & centering in main window.
        self.center_popup(direction_popup, 300, 100)

        label = tk.Label(direction_popup, text="Select the direction to export:")
        label.pack(pady=2)

        ALL_MESSAGES_SELECTION = "ALL"
        direction_var = tk.StringVar(value=ALL_MESSAGES_SELECTION)  # Default value
        directions = [ALL_MESSAGES_SELECTION] + [direction.name for direction in NetconfMessageDefs.Direction]
        dropdown = tk.OptionMenu(direction_popup, direction_var, *directions)
        dropdown.pack(pady=2)

        # Function to handle export after selection
        def handle_export():
            direction = direction_var.get()
            direction_popup.destroy()  # Close the popup

            filtered_messages = []
            for message in self.result_box.messages:
                if direction == ALL_MESSAGES_SELECTION or message.direction.name == direction:
                    filtered_messages.append(message)

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    for message in filtered_messages:
                        f.write(message.raw_data + "\n\n")
                tk.messagebox.showinfo("Export Successful", f"Exported {len(filtered_messages)} RPCs to {file_path}.")
            except Exception as e:
                tk.messagebox.showerror("Export Failed", f"Failed to export RPCs: {e}")

        export_button = tk.Button(direction_popup, text="Export", command=handle_export)
        export_button.pack(pady=5)

    def center_popup(self, popup, width, height):
        """Center a popup window relative to the main window."""
        # Calculate the position to center the popup
        main_window_x = self.winfo_x()
        main_window_y = self.winfo_y()
        main_window_width = self.winfo_width()
        main_window_height = self.winfo_height()

        x = main_window_x + (main_window_width // 2) - (width // 2)
        y = main_window_y + (main_window_height // 2) - (height // 2)

        # Set the geometry of the popup
        popup.geometry(f"{width}x{height}+{x}+{y}")
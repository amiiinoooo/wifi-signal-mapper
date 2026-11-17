import tkinter as tk
from tkinter import ttk, filedialog
import requests

ESP_URL = "http://172.20.10.10"
SERVER_URL = "http://172.20.10.2:5000" 


class WifiUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WiFi Mapper")
        self.root.geometry("1000x600")

        self.rooms = []
        self.data = {}
        self.layout_data = {}
        self.layout_loaded = False

        # ================= TOP BAR =================
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(top_frame, text="Load Layout", command=self.load_layout).pack(side="left", padx=5)

        self.room_var = tk.StringVar(value="Select a room")
        self.room_dropdown = ttk.Combobox(top_frame, textvariable=self.room_var, state="readonly")
        self.room_dropdown.pack(side="left", padx=5)

        # send room to ESP
        self.room_dropdown.bind("<<ComboboxSelected>>", self.set_room)

        self.ssid_var = tk.StringVar(value="Select a WiFi")
        self.ssid_dropdown = ttk.Combobox(top_frame, textvariable=self.ssid_var, state="readonly")
        self.ssid_dropdown.pack(side="left", padx=5)

        tk.Button(top_frame, text="Generate Heatmap", command=self.generate_heatmap).pack(side="left", padx=5)

        tk.Button(top_frame, text="Clear Data", command=self.clear_data).pack(side="right", padx=5)
        tk.Button(top_frame, text="Clear Layout", command=self.clear_layout).pack(side="right", padx=5)

        # ================= STATUS =================
        self.status = tk.Label(root, text="Load layout to begin", anchor="w")
        self.status.pack(fill="x", padx=10, pady=5)

        # ================= TABLE =================
        columns = ("Room", "SSID", "RSSI")

        self.tree = ttk.Treeview(root, columns=columns, show="headings")
        self.tree.heading("Room", text="Room")
        self.tree.heading("SSID", text="SSID")
        self.tree.heading("RSSI", text="RSSI")

        style = ttk.Style()
        style.configure("Treeview", rowheight=100)

        self.tree.pack(fill="both", expand=True)

        # background polling
        self.check_status()

    # ================= SET ROOM =================
    def set_room(self, event=None):
        room = self.room_var.get().lower()

        try:
            requests.post(f"{ESP_URL}/set_room", json={"room": room})
            self.status.config(text=f"Room set to {room} ✓ press button to scan")
        except:
            self.status.config(text="⚠ Failed to send room to ESP")

    # ================= STATUS CHECK =================
    def check_status(self):
        try:
            response = requests.get(f"{SERVER_URL}/status", timeout=1)
            if response.json().get("updated"):

                data_response = requests.get(f"{SERVER_URL}/data")
                all_data = data_response.json()

                self.process_data(all_data)
                self.status.config(text="Scan finished ✓")

                requests.post(f"{SERVER_URL}/reset")

        except:
            pass

        self.root.after(2000, self.check_status)

    # ================= LOAD LAYOUT =================
    def load_layout(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        self.rooms = []
        self.layout_data = {}

        with open(file_path, "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 5:
                    name = parts[0].strip().lower()
                    x, y, w, h = map(float, parts[1:])
                    self.rooms.append(name)
                    self.layout_data[name] = (x, y, w, h)

        self.room_dropdown["values"] = self.rooms
        self.room_var.set("Select a room")

        self.data = {room: [] for room in self.rooms}
        self.layout_loaded = True

        self.refresh_table()
        self.status.config(text="Layout loaded ✓")

    # ================= PROCESS DATA =================
    def process_data(self, all_data):
        for room, wifi_list in all_data.items():
            room = room.lower()

            if room in self.data:
                sorted_list = sorted(wifi_list, key=lambda x: x["rssi"], reverse=True)
                self.data[room] = [(w["ssid"], w["rssi"]) for w in sorted_list[:5]]

        ssids = set()
        for wifi_list in self.data.values():
            for ssid, _ in wifi_list:
                ssids.add(ssid)

        self.ssid_dropdown["values"] = list(ssids)
        self.ssid_var.set("Select a WiFi")

        self.refresh_table()

    # ================= TABLE =================
    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())

        for room in self.rooms:
            wifi_list = self.data.get(room, [])

            ssid_text = "\n".join([w[0] for w in wifi_list])
            rssi_text = "\n".join([str(w[1]) for w in wifi_list])

            self.tree.insert("", "end", values=(room, ssid_text, rssi_text))

    # ================= HEATMAP (FIXED) =================
    def generate_heatmap(self):
        if not self.layout_loaded:
            self.status.config(text="⚠ Load layout first")
            return

        if not all(self.data.get(room) for room in self.rooms):
            self.status.config(text="⚠ Scan ALL rooms first")
            return

        selected_ssid = self.ssid_var.get()
        if selected_ssid == "Select a WiFi":
            self.status.config(text="⚠ Select a WiFi")
            return

        heatmap_window = tk.Toplevel(self.root)
        heatmap_window.title("Heatmap")

        WIDTH = 900
        HEIGHT = 600

        canvas = tk.Canvas(heatmap_window, width=WIDTH, height=HEIGHT)
        canvas.pack()

        canvas.create_text(WIDTH/2, 30, text=f"{selected_ssid} Coverage", font=("Arial", 16, "bold"))

        BOX_X1, BOX_Y1 = 150, 80
        BOX_X2, BOX_Y2 = 650, 480

        canvas.create_rectangle(BOX_X1, BOX_Y1, BOX_X2, BOX_Y2, outline="black", width=2)

        CELL = 10

        def rssi_to_color(rssi):
            if rssi is None:
                return "#dddddd"
            if rssi >= -60:
                return "#00ff00"
            elif rssi >= -70:
                return "#99ff00"
            elif rssi >= -80:
                return "#ff9900"
            else:
                return "#ff0000"

        max_x = max([x + w for x, y, w, h in self.layout_data.values()])
        max_y = max([y + h for x, y, w, h in self.layout_data.values()])

        for i in range(BOX_X1, BOX_X2, CELL):
            for j in range(BOX_Y1, BOX_Y2, CELL):

                x = (i - BOX_X1) / (BOX_X2 - BOX_X1) * max_x
                y = (j - BOX_Y1) / (BOX_Y2 - BOX_Y1) * max_y

                weighted_sum = 0
                weight_total = 0

                for room, (rx, ry, rw, rh) in self.layout_data.items():
                    cx = rx + rw / 2
                    cy = ry + rh / 2

                    dist = ((cx - x)**2 + (cy - y)**2)**0.5
                    if dist < 1:
                        dist = 1

                    for ssid, rssi in self.data.get(room, []):
                        if ssid == selected_ssid:
                            weight = 1 / (dist ** 2)
                            weighted_sum += rssi * weight
                            weight_total += weight

                interpolated_rssi = weighted_sum / weight_total if weight_total > 0 else None
                color = rssi_to_color(interpolated_rssi)

                canvas.create_rectangle(i, j, i+CELL, j+CELL, fill=color, outline="")

        for room, (x, y, w, h) in self.layout_data.items():
            x1 = BOX_X1 + x / max_x * (BOX_X2 - BOX_X1)
            y1 = BOX_Y1 + y / max_y * (BOX_Y2 - BOX_Y1)
            x2 = BOX_X1 + (x + w) / max_x * (BOX_X2 - BOX_X1)
            y2 = BOX_Y1 + (y + h) / max_y * (BOX_Y2 - BOX_Y1)

            canvas.create_rectangle(x1, y1, x2, y2, outline="black", width=2)
            canvas.create_text((x1+x2)/2, (y1+y2)/2, text=room, font=("Arial", 10, "bold"))

        legend_x = 700
        legend_y = 150

        canvas.create_text(legend_x + 20, legend_y - 20, text="Signal", font=("Arial", 10, "bold"))

        legend_colors = [
            ("-30 to -60 dBm", "#00ff00"),
            ("-60 to -70 dBm", "#99ff00"),
            ("-70 to -80 dBm", "#ff9900"),
            ("< -80 dBm", "#ff0000")
        ]

        for idx, (label, color) in enumerate(legend_colors):
            y = legend_y + idx * 20
            canvas.create_rectangle(legend_x, y, legend_x+20, y+10, fill=color)
            canvas.create_text(legend_x+30, y+5, text=label, anchor="w")

        self.status.config(text=f"Heatmap generated ✓ | {selected_ssid}")

    # ================= CLEAR =================
    def clear_data(self):
        try:
            requests.post(f"{SERVER_URL}/clear")
        except:
            pass

        self.data = {room: [] for room in self.rooms}
        self.refresh_table()

        self.ssid_dropdown["values"] = []
        self.ssid_var.set("Select a WiFi")

        self.status.config(text="Data cleared ✓")

    def clear_layout(self):
        self.rooms = []
        self.data = {}
        self.layout_data = {}

        self.tree.delete(*self.tree.get_children())

        self.room_dropdown["values"] = []
        self.room_var.set("Select a room")

        self.ssid_dropdown["values"] = []
        self.ssid_var.set("Select a WiFi")

        self.layout_loaded = False

        self.status.config(text="Layout cleared ✓")

        try:
            requests.post(f"{ESP_URL}/clear_room")
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = WifiUI(root)
    root.mainloop()
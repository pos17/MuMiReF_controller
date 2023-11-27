import tkinter.messagebox
import customtkinter
import yaml
from typing import Callable
from pythonosc import udp_client
from pythonosc import osc_bundle_builder
from pythonosc import osc_message_builder
customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class BinResColumn(customtkinter.CTkFrame):
    def __init__(self, *args,
                title,
                my_client,
                index,
                width: int = 70,
                height: int = 800,
                command: Callable =None,
                **kwargs
            ):
        super().__init__(*args, width=width, height=height, **kwargs)
        self.command = command
        self.client = my_client
        self.index = index
        self.configure(fg_color=("gray78", "gray28"))  # set frame color

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.title_label = customtkinter.CTkLabel(self, text=title, font=customtkinter.CTkFont(size=16, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20,sticky="ew",columnspan=3)

        self.listen_button = customtkinter.CTkButton(self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),text="listen",command=self.listen_button_callback)
        self.listen_button.grid(row=1, column=0, padx=(5, 5), pady=(5, 5), sticky="nsew",columnspan=3)

        
        self.slider = customtkinter.CTkSlider(self, orientation="vertical")
        self.slider.grid(row=2, column=0, rowspan=5,columnspan=1, padx=(10, 0), pady=(10, 10), sticky="ns")
        self.level_meter_L = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_L.grid(row=2, column=1, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
        self.level_meter_R = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_R.grid(row=2, column=2, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
    
    def listen_button_callback(self):
        if self.command is not None:
            self.command()
        try:
            self.client.send_message("/monitoring/monitor_num",self.index)
            print("listen button index: {0}".format(self.index))

        except ValueError:
            return

class App(customtkinter.CTk):
    def __init__(self,bin_renderers,my_client):
        super().__init__()

        # configure window
        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{1100}x{580}")

         # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure((0), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="MuMiReF", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.clients_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent",orientation="horizontal")
        self.clients_frame.grid(row=0, column=1, padx=(0, 0), pady=(10, 10), sticky="nsew")
        self.clients_frame.grid_rowconfigure(1, weight=1)
        self.bin_ren_cols = []
        for i in range(len(bin_renderers)):
            bin_ren_col = BinResColumn(self.clients_frame,title=bin_renderers[i]["name"],my_client=my_client,index=i)
            bin_ren_col.grid(row=1, column=i, padx=(2, 2), pady=(0, 0), sticky="nsew")
            self.bin_ren_cols.append(bin_ren_col)
    def sidebar_button_event(self):
        print("sidebar_button click")

if __name__ == "__main__":
    with open('./config_spatial_mic_renderer_1_6.yml', 'r') as file:
        mics_config = yaml.safe_load(file) 
    renderers_num = mics_config["clients_num"]
    microphones = mics_config["microphones"]
    monitoring_setup = mics_config["monitoring"]
    REMOTE_OSC_PORT = mics_config["REMOTE_OSC_PORT"]
    jack_system = {}
    bin_renderers = [] 
    for i in range(renderers_num):
        name = microphones[i]["name"]
        OSC_port = microphones[i]["osc_port"]
        azim_deg= microphones[i]["azim_deg"]
        bin_ren ={
            "name":name,
            "OSC_port":OSC_port,
            "azim_deg":azim_deg
        }
        bin_renderers.append(bin_ren)

    ip = "127.0.0.1"
    port = 5100
    my_client = udp_client.SimpleUDPClient(ip,port)
    app = App(bin_renderers,my_client)
    app.mainloop()

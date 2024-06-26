import threading
import customtkinter
import yaml
from typing import Callable
from pythonosc import udp_client
import argparse
import numpy as np
import pythonosc.dispatcher
import pythonosc.osc_server
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.osc_server import BlockingOSCUDPServer

from pythonosc.dispatcher import Dispatcher
import asyncio


customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class MonitorColumn(customtkinter.CTkFrame):
    def __init__(self, *args,
                title,
                my_client,
                width: int = 70,
                height: int = 800,
                command: Callable =None,
                **kwargs
            ):
        super().__init__(*args, width=width, height=height, **kwargs)

        self.level_L = 0
        self.level_R = 0
        self.level_lock= threading.Lock()
        
        self.client = my_client
        self.name = title

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._mute = False
        self.mute_button = customtkinter.CTkButton(self, fg_color="transparent", border_width=2, text_color=("red"),text="MUTE",command=self.toggle_mute)
        self.mute_button.grid(row=2, column=0, padx=(5, 5), pady=(5, 5), sticky="nsew",columnspan=3)
        
        self.slider = customtkinter.CTkSlider(self, orientation="vertical", command=self.slider_event)
        self.slider.grid(row=3, column=0, rowspan=5,columnspan=1, padx=(10, 0), pady=(10, 10), sticky="ns")
        self.slider.set(np.interp(0,[-60,20],[0,1]))
        self.level_meter_L = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_L.grid(row=3, column=1, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
        self.level_meter_R = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_R.grid(row=3, column=2, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
        self.print_level_db_st(1,-60,-60)

    def slider_event(self,value):
        level_to_send = np.interp(value,[0,1],[-60,20])
        #print(value)
        try:
            message = "/" + self.name + "/volume"
            print(message)
            self.client.send_message(message,level_to_send)
            #print("listen button index: {0}".format(self.index))

        except ValueError:
            return

    def toggle_mute(self): 
        self._mute = not self._mute
        message = "/" + self.name + "/mute"
        print(message +": {0}".format(self._mute)) 
        self.client.send_message(message,self._mute)
        if self._mute:
            self.mute_button.configure(fg_color="red",text_color=("gray10", "#DCE4EE"))
            #self.level_meter_L.set(0)
            #self.level_meter_R.set(0)
        else:
            self.mute_button.configure(fg_color= "gray28",text_color="red")

    def print_level_db_st(self,unused_addr,level_db_L,level_db_R):
        self.level_lock.acquire()
        level_to_print_L = np.interp(level_db_L,[-60,+20],[0,1])
        level_to_print_R = np.interp(level_db_R,[-60,+20],[0,1])
        self.level_meter_L.set(level_to_print_L)
        self.level_meter_R.set(level_to_print_R)
        self.level_lock.release()

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
        
        self.level_L = -60
        self.level_R = -60
        self.level_changed = False
        self.level_lock = threading.Lock()
        self.tracker_lock = threading.Lock()
        self.command = command
        self.client = my_client
        self.index = index
        self.name = title
        self.configure(fg_color=("gray78", "gray28"))  # set frame color

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)
        self.title_label = customtkinter.CTkLabel(self, text=title, font=customtkinter.CTkFont(size=16, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=20,sticky="ew",columnspan=3)
        
        self.pan_label = customtkinter.CTkLabel(self, text=0, font=customtkinter.CTkFont(size=16, weight="bold"))
        self.pan_label.grid(row=1, column=0, padx=5, pady=5,sticky="ew",columnspan=3)
        
        self.pan_slider = customtkinter.CTkSlider(self, orientation="horizontal", command=self.pan_slider_event)
        self.pan_slider.grid(row=2, column=0, rowspan=1,columnspan=2, padx=(10, 0), pady=(10, 10), sticky="ns")
        self.pan_slider.set(np.interp(0.5,[-180,180],[0,1]))
        self.pan_label.configure(text=round(np.interp(0.5,[0,1],[-180,180]),1))
        self._listen = False
        self.listen_button = customtkinter.CTkButton(self, fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"),text="listen",command=self.listen_button_callback)
        self.listen_button.grid(row=3, column=0, padx=(5, 5), pady=(5, 5), sticky="nsew",columnspan=3)
        
        self._mute = False
        self.mute_button = customtkinter.CTkButton(self, fg_color="transparent", border_width=2, text_color=("red"),text="MUTE",command=self.toggle_mute)
        self.mute_button.grid(row=4, column=0, padx=(5, 5), pady=(5, 5), sticky="nsew",columnspan=3)
        
        self.slider = customtkinter.CTkSlider(self, orientation="vertical", command=self.slider_event)
        self.slider.grid(row=5, column=0, rowspan=5,columnspan=1, padx=(10, 0), pady=(10, 10), sticky="ns")
        self.slider.set(np.interp(0,[-60,+20],[0,1]))

        self.level_meter_L = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_L.grid(row=5, column=1, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
        self.level_meter_R = customtkinter.CTkProgressBar(self, orientation="vertical", progress_color="green")
        self.level_meter_R.grid(row=5, column=2, rowspan=5, padx=(10, 10), pady=(10, 10), sticky="ns")
        #self.print_level_db_st(-60,-60)
        self.level_changed= True
        self._check_and_print_level_db_st()

    def set_listen(self,is_listen):
        if is_listen:
            self.listen_button.configure(fg_color="green")
        else:
            self.listen_button.configure(fg_color= "gray28")

    def toggle_mute(self): 
        self._mute = not self._mute
        message = "/" + self.name + "renderer/mute"
        print(message +": {0}".format(self._mute)) 
        self.client.send_message(message,self._mute)
        if self._mute:
            self.mute_button.configure(fg_color="red",text_color=("gray10", "#DCE4EE"))
            #self.level_meter_L.set(0)
            #self.level_meter_R.set(0)
        else:
            self.mute_button.configure(fg_color= "gray28",text_color="red")
        


    def listen_button_callback(self):
        try:
            self.client.send_message("/monitoring/monitor_num",self.index)
            print("listen button index: {0}".format(self.index))


        except ValueError:
            return

    def print_level_db_st(self,level_db_L,level_db_R):
        level_to_print_L = np.interp(level_db_L,[-60,+20],[0,1])
        level_to_print_R = np.interp(level_db_R,[-60,+20],[0,1])
        self.level_meter_L.set(level_to_print_L)
        self.level_meter_R.set(level_to_print_R)

    def set_levels_db_st(self,unsed_addr,index_list,level_db_L,level_db_R):
        self.level_lock.acquire()
        if((level_db_L != self.level_L) or (level_db_R != self.level_R) ):
            self.level_L= level_db_L
            self.level_R= level_db_R
            self.level_changed = True
            self.print_level_db_st(self.level_L,self.level_R)
        self.level_lock.release()   

    def _check_and_print_level_db_st(self):
        self.level_lock.acquire()
        if(self.level_changed == True):
            self.print_level_db_st(self.level_L,self.level_R)
            self.level_changed= False
        self.level_lock.release()  
        #self.after(20,lambda: self._check_and_print_level_db_st)


    def slider_event(self,value):
        level_to_send = np.interp(value,[0,1],[-60,+20])
        #print(value)
        if self.command is not None:
            self.command()
        try:
            message = "/" + self.name + "renderer/volume"
            print(message)
            self.client.send_message(message,level_to_send)
            #print("listen button index: {0}".format(self.index))

        except ValueError:
            return

    def pan_slider_event(self,value):
        level_to_send = np.interp(value,[0,1],[-180,180])

        self.pan_label.configure(text=round(level_to_send,1))
        #print(value)
        if self.command is not None:
            self.command()
        try:
            message = "/" + self.name + "tracker/azimuth"
            print(message)
            self.client.send_message(message,level_to_send)
            #print("listen button index: {0}".format(self.index))

        except ValueError:
            return


    

   

    

class App(customtkinter.CTk):
    def __init__(self,bin_renderers,my_client):
        super().__init__()
        # configure window
        self.title("MumiReF controller.py")
        self.geometry(f"{1100}x{580}")

         # configure grid layout (4x4)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure((0), weight=1)

        # create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(3,weight=1)
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="MuMiReF", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.total_cpu_load_label_name = customtkinter.CTkLabel(self.sidebar_frame, text="CPU LOAD:", font=customtkinter.CTkFont(size=20))
        self.total_cpu_load_label_name.grid(row=1, column=0, padx=20, pady=(20, 10))
        self.total_cpu_load_label = customtkinter.CTkLabel(self.sidebar_frame, text="0 %", font=customtkinter.CTkFont(size=20))
        self.total_cpu_load_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.total_cpu_load_lock = threading.Lock()
        self.monitor_column = MonitorColumn(self.sidebar_frame,title="monitoring",my_client=my_client)
        self.monitor_column.grid(row=3, column=0, padx=(0, 0), pady=(10, 10), sticky="nsew")
        self.clients_frame = customtkinter.CTkScrollableFrame(self, fg_color="transparent",orientation="horizontal")
        self.clients_frame.grid(row=0, column=1, padx=(0, 0), pady=(10, 10), sticky="nsew")
        self.clients_frame.grid_rowconfigure(1, weight=1)
        self.bin_ren_cols = []
        
        
        self.OSC_client = my_client
        self.dispatcher = self.setup_osc_server("127.0.0.1",7000)
        for i in range(len(bin_renderers)):
            bin_ren_col = BinResColumn(self.clients_frame,title=bin_renderers[i]["name"],my_client=my_client,index=i)
            bin_ren_col.grid(row=1, column=i, padx=(2, 2), pady=(0, 0), sticky="nsew")
            message = "/"+ bin_renderers[i]["name"] + "renderer/peak"
            print(message)
            self.dispatcher.map(message,bin_ren_col.set_levels_db_st,i)

            message = "/monitoring/listen"
            self.dispatcher.map(message,self.listen_feedback)
            self.bin_ren_cols.append(bin_ren_col)
        self.selected_name= self.bin_ren_cols[0].name
        print(self.bin_ren_cols[0].name)
        self.dispatcher.map("/load",self.write_cpu_load)
        self.dispatcher.map("/monitoring/peak",self.monitor_column.print_level_db_st)
        self.dispatcher.map("/yaw",self.handle_ypr)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.start_action()

    def handle_ypr(self,unused_addr,y):
        print("Y:" + str(y))
        try:
            #message = "/" + self.name + "tracker/azimuth"
            message = "/" + self.selected_name + "tracker/azimuth"

            level_to_send = np.interp(y,[0,1],[-180,180])
            self.OSC_client.send_message(message,level_to_send)
            #print("listen button index: {0}".format(self.index))

        except ValueError:
            return
        

    def write_cpu_load(self,unused_addr,cpu_load):
        self.total_cpu_load_lock.acquire()
        self.total_cpu_load_label.configure(text="{0} %".format(round(cpu_load, 2)))
        self.total_cpu_load_lock.release()
    def listen_feedback(self,unused_addr,listened_index):
        for i in range(len(self.bin_ren_cols)):
            self.bin_ren_cols[i].set_listen(False)
        self.bin_ren_cols[listened_index].set_listen(True)
        self.selected_name = self.bin_ren_cols[listened_index].name


    def sidebar_button_event(self):
        print("sidebar_button click")

    def get_bin_res_col(self,index):    
        print("working")
        return self.bin_ren_cols[index]

    def start_action(self):
        self.thread = threading.Thread(target=self.init_main)
        self.thread.start()
        print("server and GUI started")
        ##self.check_thread(thread)

    def init_main(self):
        # start dispatcher,server
        ip = "127.0.0.1"
        port = 7000
        self.server = ThreadingOSCUDPServer((ip, port), self.dispatcher)
        self.server.serve_forever()  # Blocks forever
        


    def setup_osc_server(self, ip_address, inport):
        inport = inport
        parser = argparse.ArgumentParser()
        parser.add_argument("--ip", default=ip_address,
            help="The ip of the OSC server")
        parser.add_argument("--port", type=int, default=inport,
            help="The port the OSC server is listening on")
        args = parser.parse_args()
        #dispatcher = dispatcher.Dispatcher()
        dispatcher = pythonosc.dispatcher.Dispatcher()

        return dispatcher

    def on_closing(self,*args):
        self.shutting_down=True
        #self.OSC_client.send_message("/quit",0)
        #self.OSC_client.send_message("/exit",0)
        t = threading.Thread(target = self.server.shutdown)
        t.daemon = True
        t.start()
        
        print("GUI closed, stopping server")
        
        self.destroy()
        exit(0)
        #self.server.server_close()
        


if __name__ == "__main__":
    with open('./config_spatial_mic_renderer_4_test_perc.yml', 'r') as file:
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

    app = App(bin_renderers, my_client)
    ##while True:

    ##    app.update()
    app.mainloop()

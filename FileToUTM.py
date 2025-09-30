import customtkinter as ctk
from tkinter import filedialog, messagebox
import ezdxf
import simplekml
import os
import subprocess
import sys
from pyproj import Transformer
import math
from PIL import Image, ImageTk
import datetime
import colorsys
import requests
from io import BytesIO

# تنظیمات اولیه customtkinter
ctk.set_appearance_mode("light")  # حالت روشن
ctk.set_default_color_theme("blue")  # تم رنگی آبی

class DXFtoKMLConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("مبدل مختصات")
        self.root.geometry("600x400")
        self.root.configure(bg="#FFFDF5")  # رنگ نود کرم
        self.root.eval('tk::PlaceWindow . center')

        self.main_frame = ctk.CTkFrame(root, fg_color="#FFFDF5")
        self.main_frame.pack(fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="مبدل مختصات",
            font=ctk.CTkFont("Arial", 20, "bold")
        )
        self.title_label.pack(pady=15)
        self.animate_title_color(0)  # انیمیشن رنگی

        self.btn_select = ctk.CTkButton(
            self.main_frame,
            text="انتخاب فایل",
            command=self.select_file,
            width=200,
            fg_color="#e0f7fa",
            hover_color="#b2ebf2",
            text_color="black",
            corner_radius=10
        )
        self.btn_select.pack(pady=10)

        self.btn_convert = ctk.CTkButton(
            self.main_frame,
            text="تبدیل فایل",
            command=self.convert_and_open,
            width=200,
            fg_color="#c8e6c9",
            hover_color="#a5d6a7",
            text_color="black",
            state="disabled",
            corner_radius=10
        )
        self.btn_convert.pack(pady=10)

        self.status = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=ctk.CTkFont("Arial", 12),
            text_color="blue"
        )
        self.status.pack(pady=20)

        # لود لوگوها از GitHub
        try:
            right_logo_url = "https://raw.githubusercontent.com/Aminrafi76/App/refs/heads/main/logo_right.png"
            left_logo_url = "https://raw.githubusercontent.com/Aminrafi76/App/refs/heads/main/logo_left.png"

            right_logo_img = Image.open(BytesIO(requests.get(right_logo_url).content)).resize((120, 120))
            self.right_logo = ImageTk.PhotoImage(right_logo_img)
            right_label = ctk.CTkLabel(self.main_frame, image=self.right_logo, text="", fg_color="#FFFDF5")
            right_label.place(relx=1.0, rely=1.0, anchor="se")

            left_logo_img = Image.open(BytesIO(requests.get(left_logo_url).content)).resize((120, 85))
            self.left_logo = ImageTk.PhotoImage(left_logo_img)
            left_label = ctk.CTkLabel(self.main_frame, image=self.left_logo, text="", fg_color="#FFFDF5")
            left_label.place(relx=0.0, rely=1.0, anchor="sw")

        except Exception as e:
            print("❌ خطا در لود لوگوها:", e)

        self.author_label = ctk.CTkLabel(
            self.main_frame,
            text="Create By Aminrafi",
            font=ctk.CTkFont("Arial", 10),
            text_color="gray"
        )
        self.author_label.place(relx=0.5, rely=1.0, anchor="s", y=-5)

        self.utm_zone = 39
        self.utm_band = 'N'
        self.transformer = Transformer.from_crs(f"EPSG:326{self.utm_zone}", "EPSG:4326", always_xy=True)
        self.file_path = ""

    def animate_title_color(self, hue):
        r, g, b = colorsys.hsv_to_rgb(hue / 360, 1, 1)
        hex_color = f'#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}'
        self.title_label.configure(text_color=hex_color)
        self.root.after(50, self.animate_title_color, (hue + 3) % 360)

    def select_file(self):
        self.file_path = filedialog.askopenfilename(
            title="فایل DXF را انتخاب کنید",
            filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")]
        )

        if self.file_path:
            self.status.configure(text=f"فایل انتخاب شده: {os.path.basename(self.file_path)}", text_color="blue")
            self.btn_convert.configure(state="normal")
        else:
            self.status.configure(text="هیچ فایلی انتخاب نشد", text_color="red")
            self.btn_convert.configure(state="disabled")

    def convert_and_open(self):
        if not self.file_path:
            messagebox.showerror("خطا", "لطفا ابتدا یک فایل انتخاب کنید")
            return

        try:
            doc = ezdxf.readfile(self.file_path)
            modelspace = doc.modelspace()
            kml = simplekml.Kml()

            for entity in modelspace:
                self.process_entity(entity, kml)

            xs = []
            ys = []
            for entity in modelspace:
                try:
                    if entity.dxftype() in ["LINE", "LWPOLYLINE", "POLYLINE"]:
                        if entity.dxftype() == "LINE":
                            xs.extend([entity.dxf.start[0], entity.dxf.end[0]])
                            ys.extend([entity.dxf.start[1], entity.dxf.end[1]])
                        else:
                            points = entity.get_points() if entity.dxftype() == "LWPOLYLINE" else [v.dxf.location for v in entity.vertices()]
                            xs.extend([p[0] for p in points])
                            ys.extend([p[1] for p in points])
                except:
                    continue

            if xs and ys:
                center_x = sum(xs) / len(xs)
                center_y = sum(ys) / len(ys)
                lon, lat = self.utm_to_wgs84(center_x, center_y)

                kml.document.lookat = simplekml.LookAt(
                    longitude=lon,
                    latitude=lat,
                    altitude=0,
                    range=600,
                    tilt=0,
                    heading=0,
                    gxaltitudemode="relativeToGround"
                )

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.splitext(self.file_path)[0] + f"_{timestamp}.kml"
            kml.save(output_path)
            self.open_in_google_earth(output_path)

            self.status.configure(text=f"تبدیل با موفقیت انجام شد. فایل ذخیره شده: {output_path}", text_color="green")

        except Exception as e:
            messagebox.showerror("خطا در تبدیل", f"خطایی رخ داد:\n{str(e)}")
            self.status.configure(text="خطا در تبدیل فایل", text_color="red")

    def process_entity(self, entity, kml):
        try:
            if entity.dxftype() == 'LINE':
                self.convert_line(entity, kml)
            elif entity.dxftype() == 'CIRCLE':
                self.convert_circle(entity, kml)
            elif entity.dxftype() == 'LWPOLYLINE':
                self.convert_lwpolyline(entity, kml)
            elif entity.dxftype() == 'POLYLINE':
                self.convert_polyline(entity, kml)
            elif entity.dxftype() == 'POINT':
                self.convert_point(entity, kml)
            elif entity.dxftype() == 'TEXT':
                self.convert_text(entity, kml)
            elif entity.dxftype() == 'MTEXT':
                self.convert_mtext(entity, kml)
            elif entity.dxftype() == 'INSERT':
                self.convert_block(entity, kml)
        except Exception as e:
            print(f"خطا در پردازش موجودیت {entity.dxftype()}: {str(e)}")

    def utm_to_wgs84(self, x, y):
        lon, lat = self.transformer.transform(x, y)
        return lon, lat

    def convert_line(self, entity, kml):
        start = entity.dxf.start
        end = entity.dxf.end
        start_lon, start_lat = self.utm_to_wgs84(start[0], start[1])
        end_lon, end_lat = self.utm_to_wgs84(end[0], end[1])
        line = kml.newlinestring(name="Line", coords=[(start_lon, start_lat), (end_lon, end_lat)])
        line.style.linestyle.color = simplekml.Color.red
        line.style.linestyle.width = 2

    def convert_circle(self, entity, kml):
        center = entity.dxf.center
        radius = entity.dxf.radius
        center_lon, center_lat = self.utm_to_wgs84(center[0], center[1])
        circle_points = []
        for angle in range(0, 360, 10):
            rad = angle * math.pi / 180.0
            x = center[0] + radius * math.cos(rad)
            y = center[1] + radius * math.sin(rad)
            lon, lat = self.utm_to_wgs84(x, y)
            circle_points.append((lon, lat))
        circle_points.append(circle_points[0])
        pol = kml.newpolygon(name="Circle", outerboundaryis=circle_points)
        pol.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.blue)

    def convert_lwpolyline(self, entity, kml):
        points = [(self.utm_to_wgs84(vertex[0], vertex[1])) for vertex in entity.get_points()]
        if entity.closed:
            points.append(points[0])
        line = kml.newlinestring(name="Polyline", coords=points)
        line.style.linestyle.color = simplekml.Color.red
        line.style.linestyle.width = 2

    def convert_polyline(self, entity, kml):
        points = [(self.utm_to_wgs84(v.dxf.location[0], v.dxf.location[1])) for v in entity.vertices()]
        if entity.is_closed:
            points.append(points[0])
        line = kml.newlinestring(name="Polyline", coords=points)
        line.style.linestyle.color = simplekml.Color.red
        line.style.linestyle.width = 2

    def convert_point(self, entity, kml):
        location = entity.dxf.location
        lon, lat = self.utm_to_wgs84(location[0], location[1])
        point = kml.newpoint(name="Point", coords=[(lon, lat)])
        point.style.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png'

    def convert_text(self, entity, kml):
        location = entity.dxf.insert
        lon, lat = self.utm_to_wgs84(location[0], location[1])
        text = entity.dxf.text
        kml.newpoint(name=text, coords=[(lon, lat)])

    def convert_mtext(self, entity, kml):
        location = entity.dxf.insert
        lon, lat = self.utm_to_wgs84(location[0], location[1])
        text = entity.text
        kml.newpoint(name=text, coords=[(lon, lat)])

    def convert_block(self, entity, kml):
        pass

    def open_in_google_earth(self, path):
        try:
            if sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            messagebox.showerror("خطا", f"نمی‌توان فایل را باز کرد:\n{str(e)}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = DXFtoKMLConverter(root)
    root.mainloop()

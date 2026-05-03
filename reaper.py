import tkinter as tk
from tkinter import filedialog, ttk
from OpenGL.GL import *
from OpenGL.GLU import *
from pyopengltk import OpenGLFrame
import struct
import numpy as np
from datetime import datetime

class DBOViewer(OpenGLFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meshes = []
        self.camera_dist = 100
        self.wireframe = False
        self.points_only = False
        self.center = [0, 0, 0]

    def initgl(self):
        """ Initialize OpenGL state once the window is created. """
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # This is crucial: allows glColor to affect the mesh while lighting is on
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        glClearColor(0.03, 0.03, 0.03, 1.0)
        
        # Simple light setup
        glLightfv(GL_LIGHT0, GL_POSITION, (100, 200, 100, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

    def redraw(self):
        """ The main render loop called by the engine. """
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # 1. Setup Projection Matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = self.width / self.height if self.height > 0 else 1
        gluPerspective(45, aspect, 0.1, 100000.0)

        # 2. Setup ModelView Matrix (Camera)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Position camera based on the calculated center of the model
        eye_x = self.center[0] + self.camera_dist
        eye_y = self.center[1] + self.camera_dist
        eye_z = self.center[2] + self.camera_dist
        
        gluLookAt(eye_x, eye_y, eye_z, 
                  self.center[0], self.center[1], self.center[2], 
                  0, 1, 0)

        # 3. Draw Geometry
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)
        
        for mesh in self.meshes:
            glBegin(GL_TRIANGLES if not self.points_only else GL_POINTS)
            glColor3f(0.3, 0.6, 0.9)  # Slate Blue color
            for vertex in mesh:
                glVertex3fv(vertex)
            glEnd()

class ReaperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DBO REAPER PARSER")
        self.root.geometry("1200x800")
        self.root.configure(bg="#080808")

        self.setup_ui()
        
    def setup_ui(self):
        # --- Sidebar ---
        self.sidebar = tk.Frame(self.root, bg="#0f0f0f", width=320, padx=15, pady=15)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="DBO REAPER PARSER", fg="#3b82f6", bg="#0f0f0f", 
                 font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 20))

        # File Selection
        btn_file = tk.Button(self.sidebar, text="SELECT .DBO FILE", command=self.load_file, 
                             bg="#2563eb", fg="white", font=("Arial", 9, "bold"), 
                             relief="flat", pady=8)
        btn_file.pack(fill=tk.X, pady=10)

        # Stats Panel
        self.stats_frame = tk.Frame(self.sidebar, bg="#1e3a8a", padx=10, pady=10)
        self.stats_frame.pack(fill=tk.X, pady=10)
        
        self.lbl_markers = tk.Label(self.stats_frame, text="Found Markers: 0", fg="white", bg="#1e3a8a", font=("Arial", 9))
        self.lbl_markers.pack(anchor="w")
        
        self.lbl_meshes = tk.Label(self.stats_frame, text="Meshes Loaded: 0", fg="#4ade80", bg="#1e3a8a", font=("Arial", 9))
        self.lbl_meshes.pack(anchor="w")
        
        self.lbl_anims = tk.Label(self.stats_frame, text="Anim Sequences: 0", fg="#fbbf24", bg="#1e3a8a", font=("Arial", 9))
        self.lbl_anims.pack(anchor="w")

        # Hierarchy / Log
        tk.Label(self.sidebar, text="DETECTED PARTS & ANIMS", fg="#6b7280", bg="#0f0f0f", 
                 font=("Arial", 8, "bold")).pack(anchor="w", pady=(15, 5))
        
        self.hierarchy = tk.Listbox(self.sidebar, bg="#000", fg="#3b82f6", borderwidth=0, 
                                    font=("Courier", 9), selectbackground="#333")
        self.hierarchy.pack(fill=tk.BOTH, expand=True)

        # --- Viewport Area ---
        self.view_container = tk.Frame(self.root, bg="#000")
        self.view_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # OpenGL Canvas
        self.ogl_canvas = DBOViewer(self.view_container)
        self.ogl_canvas.pack(fill=tk.BOTH, expand=True)

        # Bottom Control Bar
        self.ctrl_frame = tk.Frame(self.view_container, bg="#080808", pady=10)
        self.ctrl_frame.pack(fill=tk.X)
        
        control_btns = [
            ("CENTER VIEW", self.center_view),
            ("WIREFRAME", self.toggle_wireframe),
            ("POINT CLOUD", self.toggle_points),
            ("EXPORT .OBJ", self.export_obj)
        ]
        
        for text, cmd in control_btns:
            btn = tk.Button(self.ctrl_frame, text=text, command=cmd, bg="#1f2937", fg="white", 
                            padx=15, pady=5, font=("Arial", 8, "bold"), relief="flat")
            btn.pack(side=tk.LEFT, padx=5)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.hierarchy.insert(tk.END, f"[{timestamp}] {message}")
        self.hierarchy.see(tk.END)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("DarkBasic Object", "*.dbo")])
        if not path:
            return
        
        self.log(f"Opening {path.split('/')[-1]}...")
        with open(path, "rb") as f:
            data = f.read()
            self.parse_dbo(data)

    def parse_dbo(self, data):
        self.ogl_canvas.meshes = []
        self.hierarchy.delete(0, tk.END)
        marker_count = 0
        anim_count = 0
        
        # Scan for Markers
        for i in range(len(data) - 20):
            # Geometry Marker (0x66 0x40)
            if data[i] == 0x66 and data[i+1] == 0x40:
                marker_count += 1
                mesh = self.attempt_sweep(data, i + 2)
                if mesh:
                    self.ogl_canvas.meshes.append(mesh)
                    self.log(f"Part found at offset {i}")
            
            # Animation Marker ("reap")
            if data[i:i+4] == b'reap':
                try:
                    frames = struct.unpack_from("<I", data, i + 12)[0]
                    if 0 < frames < 60000:
                        anim_count += 1
                        self.log(f"ANIM: {frames} Frames")
                except:
                    pass

        # Update Stats
        self.lbl_markers.config(text=f"Found Markers: {marker_count}")
        self.lbl_meshes.config(text=f"Meshes Loaded: {len(self.ogl_canvas.meshes)}")
        self.lbl_anims.config(text=f"Anim Sequences: {anim_count}")

        if self.ogl_canvas.meshes:
            self.center_view()
        else:
            self.log("No valid meshes extracted.")

    def attempt_sweep(self, data, start):
        """ Mimics the original JS attemptSweep logic for DarkBasic vertex strides. """
        strides = [32, 36, 40, 48, 12, 64]
        for stride in strides:
            verts = []
            p = start + 6
            # Test-sample first 50 verts to check stride validity
            for j in range(50):
                offset = p + (j * stride)
                if offset + 12 > len(data): break
                try:
                    v = struct.unpack_from("<fff", data, offset)
                    if any(abs(x) > 10000 or np.isnan(x) for x in v): break
                    verts.append(v)
                except: break
            
            if len(verts) > 10:
                # Valid stride found, extract full buffer
                full_mesh = []
                while p + 12 <= len(data):
                    v = struct.unpack_from("<fff", data, p)
                    # Out of bounds check
                    if any(abs(x) > 20000 or np.isnan(x) for x in v): break
                    full_mesh.append(v)
                    p += stride
                    if len(full_mesh) > 15000: break # Safety cap
                return full_mesh
        return None

    def center_view(self):
        if not self.ogl_canvas.meshes:
            return
        
        # Calculate AABB (Axis Aligned Bounding Box) for the model
        all_points = np.concatenate(self.ogl_canvas.meshes)
        min_p = np.min(all_points, axis=0)
        max_p = np.max(all_points, axis=0)
        
        # Calculate center and ideal camera distance
        self.ogl_canvas.center = ((min_p + max_p) / 2).tolist()
        size = np.linalg.norm(max_p - min_p)
        self.ogl_canvas.camera_dist = size if size > 5 else 50
        
        self.log("View centered on geometry.")
        self.ogl_canvas.tkExpose(None)

    def toggle_wireframe(self):
        self.ogl_canvas.wireframe = not self.ogl_canvas.wireframe
        self.ogl_canvas.tkExpose(None)

    def toggle_points(self):
        self.ogl_canvas.points_only = not self.ogl_canvas.points_only
        self.ogl_canvas.tkExpose(None)

    def export_obj(self):
        if not self.ogl_canvas.meshes:
            self.log("Nothing to export!")
            return
        
        path = filedialog.asksaveasfilename(defaultextension=".obj", filetypes=[("Wavefront OBJ", "*.obj")])
        if not path: return
        
        with open(path, "w") as f:
            f.write("# DBO Reaper Parser Export\n")
            v_offset = 1
            for idx, mesh in enumerate(self.ogl_canvas.meshes):
                f.write(f"o Part_{idx}\n")
                for v in mesh:
                    f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
                
                # Simple triangulation for export
                for i in range(0, len(mesh) - 2, 3):
                    f.write(f"f {v_offset+i} {v_offset+i+1} {v_offset+i+2}\n")
                v_offset += len(mesh)
        
        self.log("OBJ Export Complete.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReaperApp(root)
    root.mainloop()
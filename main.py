import customtkinter as ctk
import fitz  # PyMuPDF
from PIL import Image
import io

class PDFEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local PDF Editor")
        self.geometry("1366x768")
        
        # State variables
        self.doc = None
        self.current_page = 0
        
        # UI Setup
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        self.open_btn = ctk.CTkButton(self.sidebar, text="Open PDF", command=self.load_pdf)
        self.open_btn.pack(pady=20)
        
        # Pagination buttons
        self.prev_btn = ctk.CTkButton(self.sidebar, text="< Prev Page", command=self.prev_page)
        self.prev_btn.pack(pady=5)
        self.next_btn = ctk.CTkButton(self.sidebar, text="Next Page >", command=self.next_page)
        self.next_btn.pack(pady=5)
        
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.page_label = ctk.CTkLabel(self.canvas_frame, text="No PDF loaded")
        self.page_label.pack(expand=True)

    def load_pdf(self):
        # In a real app, import filedialog: filepath = ctk.filedialog.askopenfilename()
        self.doc = fitz.open("Einstein's Field Equations.pdf") # Update with your file path
        self.current_page = 0
        self.render_page()

    def render_page(self):
        if not self.doc:
            return
            
        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_data = pix.tobytes("png")
        
        pil_image = Image.open(io.BytesIO(img_data))
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pix.width, pix.height))
        
        self.page_label.configure(image=ctk_image, text="")
        self.page_label.image = ctk_image 

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

if __name__ == "__main__":
    app = PDFEditorApp()
    app.mainloop()
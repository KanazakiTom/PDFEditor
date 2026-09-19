import customtkinter as ctk
import fitz  # PyMuPDF
from PIL import Image
import io

class PDFEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local PDF Editor")
        self.geometry("1366x768")
        
        # UI Setup
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        self.open_btn = ctk.CTkButton(self.sidebar, text="Open PDF", command=self.load_pdf)
        self.open_btn.pack(pady=20)
        
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.page_label = ctk.CTkLabel(self.canvas_frame, text="No PDF loaded")
        self.page_label.pack(expand=True)

    def load_pdf(self):
        # In a real app, use ctk.filedialog.askopenfilename()
        doc = fitz.open("sample.pdf")
        page = doc.load_page(0)  # Load first page
        
        # Render page to an image (Pixmap)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # Scale up for clarity
        img_data = pix.tobytes("png")
        
        # Convert to a format CustomTkinter can display
        pil_image = Image.open(io.BytesIO(img_data))
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pix.width, pix.height))
        
        self.page_label.configure(image=ctk_image, text="")
        self.page_label.image = ctk_image # Keep reference

if __name__ == "__main__":
    app = PDFEditorApp()
    app.mainloop()
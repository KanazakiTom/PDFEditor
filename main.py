import customtkinter as ctk
import pymupdf as fitz
from PIL import Image
import io

class PDFEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local PDF Editor")
        self.geometry("1366x768")
        
        self.doc = None
        self.current_page = 0
        self.edit_mode = False # Track if we are trying to add text
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        self.open_btn = ctk.CTkButton(self.sidebar, text="Open PDF", command=self.load_pdf)
        self.open_btn.pack(pady=20)
        
        self.prev_btn = ctk.CTkButton(self.sidebar, text="< Prev Page", command=self.prev_page)
        self.prev_btn.pack(pady=5)
        self.next_btn = ctk.CTkButton(self.sidebar, text="Next Page >", command=self.next_page)
        self.next_btn.pack(pady=5)
        
        # New: Add Text Button
        self.add_text_btn = ctk.CTkButton(self.sidebar, text="Add Text Tool", command=self.enable_text_mode)
        self.add_text_btn.pack(pady=20)
        
        # Canvas
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.page_label = ctk.CTkLabel(self.canvas_frame, text="No PDF loaded")
        self.page_label.pack(expand=True)
        
        # Bind mouse click to the label
        self.page_label.bind("<Button-1>", self.on_canvas_click)

    def load_pdf(self):
        self.doc = fitz.open("Einstein's Field Equations.pdf") # Update with your file path
        self.current_page = 0
        self.render_page()

    def render_page(self):
        if not self.doc:
            return
            
        page = self.doc.load_page(self.current_page)
        # We scale by 1.5x for UI clarity. We must remember this for coordinate mapping.
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_data = pix.tobytes("png")
        
        pil_image = Image.open(io.BytesIO(img_data))
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(pix.width, pix.height))
        
        self.page_label.configure(image=ctk_image, text="")
        self.page_label.image = ctk_image 

    def enable_text_mode(self):
        self.edit_mode = True
        self.add_text_btn.configure(text="Click on page to add...", fg_color="green")

    def on_canvas_click(self, event):
        if not self.edit_mode or not self.doc:
            return
            
        # 1. Ask user for the text
        dialog = ctk.CTkInputDialog(text="Enter text to add:", title="Insert Text")
        new_text = dialog.get_input()
        
        if new_text:
            page = self.doc.load_page(self.current_page)
            
            # 2. Map UI coordinates back to PDF coordinates
            # Because we scaled the image by 1.5 in render_page, we divide the click coordinates by 1.5
            pdf_x = event.x / 1.5
            pdf_y = event.y / 1.5
            
            # 3. Insert text into the PDF
            point = fitz.Point(pdf_x, pdf_y)
            page.insert_text(point, new_text, fontsize=12, color=(0, 0, 0))
            
            # 4. Re-render to show the changes
            self.render_page()
            
        # Reset tool
        self.edit_mode = False
        self.add_text_btn.configure(text="Add Text Tool", fg_color=["#3a7ebf", "#1f538d"]) # Default CTk blue

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
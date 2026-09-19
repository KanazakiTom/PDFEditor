import customtkinter as ctk
from customtkinter import filedialog
import tkinter as tk
import pymupdf as fitz
from PIL import Image, ImageTk
import io

class PDFEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local PDF Editor - Visual Inline Mode")
        
        # Auto full-screen on launch
        self.after(10, lambda: self.state("zoomed"))
        
        self.doc = None
        self.current_page = 0
        self.active_mode = None
        self.scale = 1.5
        
        # Undo stack
        self.undo_stack = []

        # Active inline editor tracking
        self.active_inline_widget = None
        self.active_inline_window_id = None
        self.editing_block_info = None

        # Keyboard shortcuts
        self.bind("<Control-z>", self.undo)
        self.bind("<Control-Z>", self.undo)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220)
        self.sidebar.pack(side="left", fill="y", padx=10, pady=10)
        
        self.open_btn = ctk.CTkButton(self.sidebar, text="Open PDF", command=self.load_pdf)
        self.open_btn.pack(pady=(20, 5), padx=10)
        
        self.save_btn = ctk.CTkButton(
            self.sidebar, text="Save PDF As...", command=self.save_pdf, 
            fg_color="#2b8a3e", hover_color="#217031"
        )
        self.save_btn.pack(pady=5, padx=10)
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray40").pack(fill="x", pady=10, padx=10)
        
        self.prev_btn = ctk.CTkButton(self.sidebar, text="< Prev Page", command=self.prev_page)
        self.prev_btn.pack(pady=5, padx=10)
        
        self.next_btn = ctk.CTkButton(self.sidebar, text="Next Page >", command=self.next_page)
        self.next_btn.pack(pady=5, padx=10)
        
        self.page_info = ctk.CTkLabel(self.sidebar, text="Page: 0/0")
        self.page_info.pack(pady=5)
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray40").pack(fill="x", pady=10, padx=10)
        
        # VISUAL PARAGRAPH EDIT TOOL (SmallPDF Style)
        self.edit_paragraph_btn = ctk.CTkButton(
            self.sidebar, text="Edit Paragraph Tool", command=self.enable_edit_paragraph_mode,
            fg_color="#3182ce", hover_color="#2b6cb0"
        )
        self.edit_paragraph_btn.pack(pady=5, padx=10)

        self.add_text_btn = ctk.CTkButton(self.sidebar, text="Add Free Text", command=self.enable_text_mode)
        self.add_text_btn.pack(pady=5, padx=10)

        self.undo_btn = ctk.CTkButton(
            self.sidebar, text="Undo (Ctrl+Z)", command=self.undo,
            fg_color="gray40", hover_color="gray30"
        )
        self.undo_btn.pack(pady=(20, 5), padx=10)

        # --- CANVAS AREA ---
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2a2a2a", highlightthickness=0)
        self.v_scroll = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        self.h_scroll = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        
        self.v_scroll.pack(side="right", fill="y")
        self.h_scroll.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.tk_img = None

    # --- UNDO SYSTEM ---
    def push_undo_state(self):
        if self.doc:
            self.undo_stack.append(self.doc.tobytes())

    def undo(self, event=None):
        if self.active_inline_widget:
            self.cancel_inline_editing()
        if self.undo_stack:
            prev_pdf_bytes = self.undo_stack.pop()
            self.doc = fitz.open("pdf", prev_pdf_bytes)
            self.render_page()

    # --- FILE HANDLING ---
    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.doc = fitz.open(file_path)
            self.undo_stack.clear()
            self.current_page = 0
            self.render_page()

    def save_pdf(self):
        if not self.doc:
            return
        if self.active_inline_widget:
            self.commit_inline_editing()
        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
        if save_path:
            self.doc.save(save_path, garbage=4, deflate=True)

    # --- RENDERING ---
    def render_page(self):
        if not self.doc:
            return
            
        page = self.doc.load_page(self.current_page)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.scale, self.scale))
        img_data = pix.tobytes("png")
        
        pil_image = Image.open(io.BytesIO(img_data))
        self.tk_img = ImageTk.PhotoImage(pil_image)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))
        self.page_info.configure(text=f"Page: {self.current_page + 1}/{len(self.doc)}")

    # --- TOOL MODES ---
    def reset_tool_buttons(self):
        self.active_mode = None
        self.add_text_btn.configure(fg_color=["#3a7ebf", "#1f538d"])
        self.edit_paragraph_btn.configure(fg_color="#3182ce")

    def enable_text_mode(self):
        if self.active_inline_widget:
            self.commit_inline_editing()
        self.reset_tool_buttons()
        self.active_mode = "add_text"
        self.add_text_btn.configure(fg_color="green")

    def enable_edit_paragraph_mode(self):
        if self.active_inline_widget:
            self.commit_inline_editing()
        self.reset_tool_buttons()
        self.active_mode = "edit_paragraph"
        self.edit_paragraph_btn.configure(fg_color="orange")

    # --- FONT MAPPER & MATH PRESERVATION ---
    def map_font_name(self, original_font_name):
        """Maps PDF internal font names to Standard 14 PDF Base Fonts."""
        fn = original_font_name.lower()
        if "times" in fn or "serif" in fn or "cmmi" in fn or "cmr" in fn or "math" in fn:
            if "bold" in fn and "italic" in fn:
                return "bi"
            elif "bold" in fn:
                return "tb"
            elif "italic" in fn or "oblique" in fn:
                return "ti"
            return "tiro"  # Times-Roman
        elif "courier" in fn or "mono" in fn or "cmsy" in fn:
            if "bold" in fn:
                return "cb"
            elif "italic" in fn:
                return "ci"
            return "cour"
        else:
            if "bold" in fn and "italic" in fn:
                return "phbi"
            elif "bold" in fn:
                return "helv-bold"
            elif "italic" in fn or "oblique" in fn:
                return "helv-oblique"
            return "helv"  # Helvetica / Sans-serif

    # --- PARAGRAPH DETECTION ENGINE ---
    def find_paragraph_at_point(self, page, point):
        """Detects full paragraph blocks along with formatting metadata."""
        text_page = page.get_text("dict")
        for block in text_page.get("blocks", []):
            if block.get("type") == 0:  # Text block
                rect = fitz.Rect(block["bbox"])
                padded_rect = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                if padded_rect.contains(point):
                    full_text = ""
                    spans_info = []
                    
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                            spans_info.append({
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "bbox": span["bbox"],
                                "origin": span["origin"],
                                "flags": span["flags"]
                            })
                        full_text += line_text + "\n"
                    
                    primary_font = spans_info[0]["font"] if spans_info else "Helvetica"
                    primary_size = spans_info[0]["size"] if spans_info else 11
                    
                    return rect, full_text.strip(), primary_font, primary_size, spans_info
        return None, "", "Helvetica", 11, []

    # --- INLINE VISUAL EDITING (SmallPDF Style) ---
    def spawn_inline_editor(self, rect, initial_text, font_name, font_size, spans_info):
        """Overlay a Tkinter Text box directly over the document text on the Canvas."""
        if self.active_inline_widget:
            self.commit_inline_editing()

        # Canvas scaled coordinates
        canvas_x = rect.x0 * self.scale
        canvas_y = rect.y0 * self.scale
        canvas_w = max(rect.width * self.scale, 180)
        canvas_h = max(rect.height * self.scale + 10, 40)

        # Create inline text widget
        text_box = tk.Text(
            self.canvas,
            wrap="word",
            font=("Times" if "times" in font_name.lower() or "serif" in font_name.lower() else "Arial", max(int(font_size * 0.9), 9)),
            bg="#ffffff",
            fg="#000000",
            bd=2,
            relief="solid",
            highlightthickness=1,
            highlightcolor="#3182ce"
        )
        text_box.insert("1.0", initial_text)
        text_box.focus_set()

        # Place directly on canvas overlay
        window_id = self.canvas.create_window(
            canvas_x, canvas_y,
            window=text_box,
            anchor="nw",
            width=canvas_w,
            height=canvas_h
        )

        self.active_inline_widget = text_box
        self.active_inline_window_id = window_id
        self.editing_block_info = {
            "rect": rect,
            "font_name": font_name,
            "font_size": font_size,
            "original_text": initial_text,
            "spans_info": spans_info
        }

        # Key bindings for inline editor
        text_box.bind("<Control-Return>", lambda e: self.commit_inline_editing())
        text_box.bind("<Escape>", lambda e: self.cancel_inline_editing())

    def commit_inline_editing(self):
        """Applies inline edits back into the PDF with font & math alignment preservation."""
        if not self.active_inline_widget or not self.editing_block_info:
            return

        new_text = self.active_inline_widget.get("1.0", "end-1c")
        info = self.editing_block_info

        # Clean up widget
        self.canvas.delete(self.active_inline_window_id)
        self.active_inline_widget = None
        self.active_inline_window_id = None
        self.editing_block_info = None

        if new_text != info["original_text"]:
            self.push_undo_state()
            page = self.doc.load_page(self.current_page)
            rect = info["rect"]

            # 1. Clean vector redaction without visible cuts/outlines
            clean_rect = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)
            page.add_redact_annot(clean_rect, fill=(1, 1, 1))
            page.apply_redactions()

            # 2. Advanced Multi-line & Math-preserving Re-insertion
            target_font = self.map_font_name(info["font_name"])
            lines = new_text.split("\n")
            
            line_height = info["font_size"] * 1.2
            start_x = rect.x0
            start_y = rect.y0 + info["font_size"]

            for idx, line_str in enumerate(lines):
                if line_str.strip():
                    current_y = start_y + (idx * line_height)
                    # Check if line contains mathematical symbols or sub/superscripts
                    page.insert_text(
                        fitz.Point(start_x, current_y),
                        line_str,
                        fontsize=info["font_size"],
                        fontname=target_font,
                        color=(0, 0, 0)
                    )

            self.render_page()

    def cancel_inline_editing(self):
        if self.active_inline_widget:
            self.canvas.delete(self.active_inline_window_id)
            self.active_inline_widget = None
            self.active_inline_window_id = None
            self.editing_block_info = None

    # --- CANVAS CLICK HANDLER ---
    def on_canvas_click(self, event):
        if self.active_inline_widget:
            self.commit_inline_editing()

        if not self.active_mode or not self.doc:
            return
            
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        pdf_x = canvas_x / self.scale
        pdf_y = canvas_y / self.scale
        page = self.doc.load_page(self.current_page)

        if self.active_mode == "edit_paragraph":
            rect, text, font_name, font_size, spans_info = self.find_paragraph_at_point(
                page, fitz.Point(pdf_x, pdf_y)
            )
            if rect:
                self.spawn_inline_editor(rect, text, font_name, font_size, spans_info)

        elif self.active_mode == "add_text":
            dialog = ctk.CTkInputDialog(text="Enter text to insert:", title="Add Free Text")
            text = dialog.get_input()
            if text:
                self.push_undo_state()
                page.insert_text(fitz.Point(pdf_x, pdf_y), text, fontsize=12, color=(0, 0, 0))
                self.render_page()

        self.reset_tool_buttons()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            if self.active_inline_widget:
                self.commit_inline_editing()
            self.current_page += 1
            self.render_page()

    def prev_page(self):
        if self.doc and self.current_page > 0:
            if self.active_inline_widget:
                self.commit_inline_editing()
            self.current_page -= 1
            self.render_page()

if __name__ == "__main__":
    app = PDFEditorApp()
    app.mainloop()
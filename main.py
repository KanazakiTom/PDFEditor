import customtkinter as ctk
from customtkinter import filedialog
import tkinter as tk
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import io

# Custom modal dialog that pre-fills existing sentence text (like SmallPDF)
class EditSentenceDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_text=""):
        super().__init__(parent)
        self.title("Edit Sentence")
        self.geometry("520x180")
        self.resizable(False, False)
        self.result = None

        self.label = ctk.CTkLabel(self, text="Edit selected sentence:", font=("Arial", 13, "bold"))
        self.label.pack(pady=(15, 5), padx=20, anchor="w")

        self.entry = ctk.CTkEntry(self, width=480, font=("Arial", 12))
        self.entry.pack(pady=10, padx=20)
        self.entry.insert(0, initial_text)
        self.entry.select_range(0, tk.END)
        self.entry.focus()

        # Keyboard shortcuts for dialog
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10, padx=20, fill="x")

        self.ok_btn = ctk.CTkButton(self.btn_frame, text="Apply Edit", command=self.on_ok, width=110, fg_color="#2b8a3e")
        self.ok_btn.pack(side="right", padx=5)

        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", command=self.on_cancel, width=90, fg_color="gray50")
        self.cancel_btn.pack(side="right", padx=5)

        self.transient(parent)
        self.grab_set()
        parent.wait_window(self)

    def on_ok(self):
        self.result = self.entry.get()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


class PDFEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Local PDF Editor")
        
        # 1. AUTO FULL-SCREEN (Maximized Window)
        self.after(10, lambda: self.state("zoomed"))
        
        self.doc = None
        self.current_page = 0
        self.active_mode = None
        self.scale = 1.5
        
        # Undo history stack (stores PDF document byte snapshots)
        self.undo_stack = []

        # 2. KEYBOARD SHORTCUT: Ctrl + Z to Undo
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
        
        # 3. EDIT SENTENCE / LINE TOOL (SmallPDF Style)
        self.edit_sentence_btn = ctk.CTkButton(
            self.sidebar, text="Edit Sentence Tool", command=self.enable_edit_sentence_mode,
            fg_color="#3182ce", hover_color="#2b6cb0"
        )
        self.edit_sentence_btn.pack(pady=5, padx=10)

        self.add_text_btn = ctk.CTkButton(self.sidebar, text="Add Free Text", command=self.enable_text_mode)
        self.add_text_btn.pack(pady=5, padx=10)

        self.undo_btn = ctk.CTkButton(
            self.sidebar, text="Undo (Ctrl+Z)", command=self.undo,
            fg_color="gray40", hover_color="gray30"
        )
        self.undo_btn.pack(pady=(20, 5), padx=10)

        # --- CANVAS AREA WITH SCROLLBARS ---
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
        """Saves current state of the document bytes into memory for Ctrl+Z."""
        if self.doc:
            self.undo_stack.append(self.doc.tobytes())

    def undo(self, event=None):
        """Restores previous document state when Ctrl+Z is pressed."""
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
        self.edit_sentence_btn.configure(fg_color="#3182ce")

    def enable_text_mode(self):
        self.reset_tool_buttons()
        self.active_mode = "add_text"
        self.add_text_btn.configure(fg_color="green")

    def enable_edit_sentence_mode(self):
        self.reset_tool_buttons()
        self.active_mode = "edit_sentence"
        self.edit_sentence_btn.configure(fg_color="orange")

    # --- LINE/SENTENCE DETECTION ENGINE ---
    def find_line_at_point(self, page, point):
        """Scans the page structure to find the full text line under the click coordinates."""
        text_page = page.get_text("dict")
        for block in text_page.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    rect = fitz.Rect(line["bbox"])
                    # Slightly expand click target box for easier clicking
                    padded_rect = fitz.Rect(rect.x0 - 2, rect.y0 - 2, rect.x1 + 2, rect.y1 + 2)
                    if padded_rect.contains(point):
                        full_sentence = "".join([span["text"] for span in line["spans"]])
                        font_size = line["spans"][0]["size"] if line["spans"] else 11
                        return rect, full_sentence.strip(), font_size
        return None, "", 11

    # --- CANVAS CLICK HANDLER ---
    def on_canvas_click(self, event):
        if not self.active_mode or not self.doc:
            return
            
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        pdf_x = canvas_x / self.scale
        pdf_y = canvas_y / self.scale
        page = self.doc.load_page(self.current_page)

        if self.active_mode == "edit_sentence":
            # Detect sentence box at click position
            line_rect, existing_text, font_size = self.find_line_at_point(page, fitz.Point(pdf_x, pdf_y))

            if line_rect:
                # Open SmallPDF-style pre-filled popup dialog
                dialog = EditSentenceDialog(self, initial_text=existing_text)
                new_text = dialog.result

                if new_text is not None and new_text != existing_text:
                    # Save snapshot before modifying
                    self.push_undo_state()

                    # 1. Cleanly redact the old sentence (no left-over cuts or artifacts)
                    # Expand rect by 1pt to guarantee full vector coverage
                    clean_rect = fitz.Rect(line_rect.x0 - 1, line_rect.y0 - 1, line_rect.x1 + 1, line_rect.y1 + 1)
                    page.add_redact_annot(clean_rect, fill=(1, 1, 1))
                    page.apply_redactions()

                    # 2. Insert new edited text aligned seamlessly at the baseline
                    if new_text.strip():
                        page.insert_text(
                            fitz.Point(line_rect.x0, line_rect.y1 - 2), 
                            new_text, 
                            fontsize=font_size, 
                            color=(0, 0, 0)
                        )

        elif self.active_mode == "add_text":
            dialog = ctk.CTkInputDialog(text="Enter text to insert:", title="Add Free Text")
            text = dialog.get_input()
            if text:
                self.push_undo_state()
                page.insert_text(fitz.Point(pdf_x, pdf_y), text, fontsize=12, color=(0, 0, 0))

        self.reset_tool_buttons()
        self.render_page()

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
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("tours-example/НВП6-1.pdf")
content = result.document.export_to_markdown()
with open("assistant-example.md", "wt") as f:
   f.write(content)

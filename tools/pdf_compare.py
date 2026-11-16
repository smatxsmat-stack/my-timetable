"""Advisory PDF comparison only: never authorizes automatic publication."""
import difflib,io,json
from pathlib import Path
import pdfplumber

def compare(old_bytes,new_bytes,target):
 def text(raw):
  with pdfplumber.open(io.BytesIO(raw)) as d:
   if len(d.pages)>20:raise ValueError('Too many PDF pages')
   return '\n'.join(f'PAGE {i+1}\n'+(p.extract_text(layout=True) or '') for i,p in enumerate(d.pages))
 old,new=text(old_bytes),text(new_bytes)
 Path(target).write_text('NOT VALIDATED: layout/text differences require human review.\n'+''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='accepted PDF',tofile='official candidate PDF')))

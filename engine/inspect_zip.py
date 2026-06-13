import zipfile
import sys

z = zipfile.ZipFile(r"g:\projects\sandbench\testing 2.zip")
for info in z.infolist():
    print(f"  {info.filename}  ({info.file_size} bytes)")
z.close()

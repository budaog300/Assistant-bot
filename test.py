from PyPDF2 import PdfReader
import pathlib
mypath = "yandex-assistant/files-example"
def read_file(file):
    res = []
    try:
        if file.suffix == '.pdf':            
            try:
                with open(file, 'rb') as f:
                    reader = PdfReader(f)
                    res.append(" ".join(page.extract_text() for page in reader.pages))
                    return res if res else []
            except UnicodeDecodeError:
                print(f'Ошибка кодировки у файла {file}')
        else:
            with open(file, 'r', encoding='utf-8') as f:
                res.append(f.read())
                return res
    except FileNotFoundError:
        print(f'Файл {file} не найден!')
        return []
    except Exception as e:
        print(f'Ошибка при чтении файа {file}: {e}')
        return []
        

paths = pathlib.Path(mypath).iterdir()

files = ['files-example/test.txt', 'files-example/test1.txt'] 
res = []
for path in paths:    
    content = read_file(path)
    if content:
        res.extend(content)
print(res)
print(len(res))
# print('\n'.join(res))
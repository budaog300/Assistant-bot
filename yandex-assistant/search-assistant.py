#!/usr/bin/env python3

from __future__ import annotations
from PyPDF2 import PdfReader
import json
import pathlib
import re
import numpy as np
import os
from dotenv import load_dotenv
from scipy.spatial.distance import cdist
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk.search_indexes import (
    HybridSearchIndexType,
    StaticIndexChunkingStrategy,
    TextSearchIndexType,
    ReciprocalRankFusionIndexCombinationStrategy,
    VectorSearchIndexType,
)
load_dotenv() 
mypath = "files-example"

instruction = """    
    ЖЕСТКИЕ ПРАВИЛА:
        1. ЗАПРЕЩЕНО ссылаться на интернет или внешние источники
        2. ЗАПРЕЩЕНО говорить, что в интернете есть много сайтов с информацией на эту тему
        3. ЗАПРЕЩЕНО добавлять в ответ любые URL-адреса
        4. Если ответа нет в файлах - говори ТОЛЬКО: "В файлах нет информации по этому поводу"
        5. Не предлагай искать информацию в других источниках
        6. Не извиняйся за отсутствие информации
    Ты - эксперт-помощник по внутренней документации, который отвечает ИСКЛЮЧИТЕЛЬНО на основе предоставленных файлов. 
    Принципы: семантическое понимание запроса, контекстуализация, полнота ответа.
    Правила: 
    - отвечай вежливо и профессионально
    - ищи информацию семантически, не только по точному совпадению слов
    - если есть релевантная информация - предоставь её полностью    
"""


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
        

def get_answer_by_embeddings(sdk, query, doc_texts):
    # Создаем эмбеддинг запроса
    query_model = sdk.models.text_embeddings("query")
    query_embedding = query_model.run(query)

    # Создаем эмбеддинг текстов
    doc_model = sdk.models.text_embeddings("doc")
    doc_embeddings = [doc_model.run(text) for text in doc_texts]

    query_embedding = np.array(query_embedding)

    # Вычисляем косинусные расстояния и находим ближайшие вектора
    dist = cdist([query_embedding], doc_embeddings, metric="cosine")
    sim = 1 - dist
    res = doc_texts[np.argmax(sim)]
    return clean_text(res)


def clean_text(text):
        # Удаляем лишние переносы строк и пробелы
        text = ' '.join(text.split())          
        # Удаляем двойные пробелы
        text = re.sub(r'\s+', ' ', text)
        # Удаляем одиночные переносы строк внутри предложений
        text = text.replace('\n', ' ').replace('\r', ' ')
        # Капитализируем первое слово
        if text:
            text = text[0].upper() + text[1:]
        return text.strip()


index_label = {
    "promo": "Индекс содержит общую информацию о Бали и Казахстане",
    "visas": "Индекс содержит информацию о визовой политике при въезде на Бали и в Казахстан",
}

def main():
    sdk = YCloudML(
        folder_id=os.getenv("YCLOUD_FOLDER_ID"),
        auth=os.getenv("YCLOUD_AUTH"),
    )

    paths = pathlib.Path(mypath).iterdir()

    # Загрузим файлы с примерами.
    # Файлы будут храниться 5 дней.
    files = []
    doc_texts = []
    for path in paths:
        # content = read_file(path)
        # if content:
        #     doc_texts.extend(content)
        file = sdk.files.upload(
            path,
            ttl_days=5,
            expiration_policy="static",
            timeout=120.0 
        )
        files.append(file)   
    
    # Создадим индекс для полнотекстового поиска по загруженным файлам.
    # В данном примере задается размер фрагмента,
    # не превышающий 700 токенов с перекрытием в 300 токенов.
    operation = sdk.search_indexes.create_deferred(
        files,
        index_type=VectorSearchIndexType(),
        
        # index_type=TextSearchIndexType(
        #     chunking_strategy=StaticIndexChunkingStrategy(
        #         max_chunk_size_tokens=1024,
        #         chunk_overlap_tokens=512,
        #     ),
        #     # combination_strategy=ReciprocalRankFusionIndexCombinationStrategy(),
        # ),
    )

    # Дождемся создания поискового индекса.
    search_index = operation.wait()

    # Создадим инструмент для работы с поисковым индексом.
    # Или даже с несколькими индексами, если бы их было больше.
    tool = sdk.tools.search_index(search_index)
    model = sdk.models.completions("yandexgpt", model_version="rc").configure(temperature=0.2)
    # Создадим ассистента для модели YandexGPT Pro Latest.
    # Он будет использовать инструмент поискового индекса.
    assistant = sdk.assistants.create(
        model, 
        instruction = instruction, 
        tools=[tool]
    )
    thread = sdk.threads.create()

    input_text = input(
        'Введите ваш вопрос ассистенту ("exit" - чтобы завершить диалог): '
    )    
    
    while input_text.lower() != "exit":
        thread.write(input_text)

        # Отдаем модели все содержимое треда.
        run = assistant.run(thread)

        # Чтобы получить результат, нужно дождаться окончания запуска.
        result = run.wait()
       
        # Выводим на экран часть атрибутов свойства citations — информацию
        # об использованных фрагментах, созданных из файлов-источников.
        # Чтобы вывести на экран все содержимое свойства citations,
        # выполните: print(result.citations)
        count = 1
        for citation in result.citations:
            for source in citation.sources:
                if source.type != "filechunk":
                    continue
                doc_texts.append(source.parts[0])
                print(
                    f"* Содержимое фрагмента №{count}: {source.parts}"
                )
                # print(
                #     f"* Идентификатор поискового индекса в фрагменте №{count}: {source.search_index.id}"
                # )
                # print(
                #     f"* Настройки типа поискового индекса в фрагменте №{count}: {source.search_index.index_type}"
                # )
                # print(
                #     f"* Идентификатор файла-источника для фрагмента №{count}: {source.file.id}"
                # )
                # print(
                #     f"* MIME-тип файла-источника для фрагмента №{count}: {source.file.mime_type}"
                # )
                print()

            count += 1
        answer = result.text
        
        # Выводим на экран ответ. 
        if 'http' in answer.lower():
            answer = get_answer_by_embeddings(sdk, input_text, doc_texts)
            print("Ответ: ", answer)
        else:            
            print("Ответ: ", answer)
        doc_texts.clear()
        input_text = input(
            'Введите ваш вопрос ассистенту ("exit" - чтобы завершить диалог): '
        ).strip()
        
        response = {
            "answer": answer,  
        }
        json.dumps(response)
    # Удаляем все ненужное.
    search_index.delete()
    thread.delete()
    assistant.delete()

    for file in files:
        file.delete()


if __name__ == "__main__":
    main()

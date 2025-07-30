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

index_label = {
    "promo": "Индекс содержит общую информацию о Бали и Казахстане",
    "visas": "Индекс содержит информацию о визовой политике при въезде на Бали и в Казахстан",
}


class Assistant:
    def __init__(self):        
        self.doc_texts = []
        mypath = "files-example"
        current_dir = os.path.dirname(os.path.abspath(__file__))
        mypath = os.path.join(current_dir, "files-example")
    
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
        self.sdk = YCloudML(
            folder_id=os.getenv("YCLOUD_FOLDER_ID"),
            auth=os.getenv("YCLOUD_AUTH"),
        )

        paths = pathlib.Path(mypath).iterdir()

        # Загрузим файлы с примерами.
        # Файлы будут храниться 5 дней.
        self.files = []        
        for path in paths:            
            file = self.sdk.files.upload(
                path,
                ttl_days=5,
                expiration_policy="static",
                timeout=120.0 
            )
            self.files.append(file)   
        
        # Создадим индекс для полнотекстового поиска по загруженным файлам.
        # В данном примере задается размер фрагмента,
        # не превышающий 700 токенов с перекрытием в 300 токенов.
        operation = self.sdk.search_indexes.create_deferred(
            self.files,
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
        self.search_index = operation.wait()

        # Создадим инструмент для работы с поисковым индексом.
        # Или даже с несколькими индексами, если бы их было больше.
        tool = self.sdk.tools.search_index(self.search_index)
        model = self.sdk.models.completions("yandexgpt", model_version="rc").configure(temperature=0.2)
        # Создадим ассистента для модели YandexGPT Pro Latest.
        # Он будет использовать инструмент поискового индекса.
        self.assistant = self.sdk.assistants.create(
            model, 
            instruction = instruction, 
            tools=[tool]
        )
        self.thread = self.sdk.threads.create()
    
    def get_answer_by_embeddings(self, sdk, query, doc_texts):
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
        return self.clean_text(res)

    @staticmethod
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

    @staticmethod
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
          
    def ask(self, query):
        # query = input(
        #     'Введите ваш вопрос ассистенту ("exit" - чтобы завершить диалог): '
        # )    
        
        # while query.lower() != "exit":
        self.thread.write(query)

        # Отдаем модели все содержимое треда.
        run = self.assistant.run(self.thread)

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
                self.doc_texts.append(source.parts[0])
                # print(
                #     f"* Содержимое фрагмента №{count}: {source.parts}"
                # )
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
                # print()

            count += 1
        answer = result.text
        
        # Выводим на экран ответ. 
        if 'http' in answer.lower():
            answer = self.get_answer_by_embeddings(self.sdk, query, self.doc_texts)   
        # print("Ответ: ", answer)
        self.doc_texts.clear()
        # query = input(
        #     'Введите ваш вопрос ассистенту ("exit" - чтобы завершить диалог): '
        # ).strip()
        
        response = {
            "answer": answer,  
        }
        return response            
        # json.dumps(response)  

    def shutdown(self):
        # Удаляем все ненужное.
        self.search_index.delete()
        self.thread.delete()
        self.assistant.delete()

        for file in self.files:
            file.delete()


# if __name__ == "__main__":
#     app = Assistant()
#     app.ask()

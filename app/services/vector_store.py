import json
import logging
import os

logger = logging.getLogger("JARVIS")

class VectorStoreService:
    def __init__(self, data_dir: str = "database/chats_data"):
        self.data_dir = data_dir
        self.documents = []

        if os.path.exists(self.data_dir):
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.data_dir, filename), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            for msg in data.get("messages", []):
                                self.documents.append({"content": msg.get("content", ""), "source": filename})
                    except Exception as e:
                        logger.warning(f"Skipping file {filename}: {e}")
            
            logger.info(f"Loaded {len(self.documents)} documents.")

    def get_retriever(self, k: int = 10):
        docs = self.documents

        class MockRetriever:
            def __init__(self, doc_list, k):
                self.docs = doc_list
                self.k = k

            def invoke(self, question):
                return self.docs[-self.k:] if self.docs else []

        return MockRetriever(docs, k)
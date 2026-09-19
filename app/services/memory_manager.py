import json
import logging
from pathlib import Path

logger = logging.getLogger("JARVIS")


class MemoryManager:
    def __init__(self, memory_file="database/learning_data/memories.json"):
        self.memory_file = Path(memory_file)
        self.memories = []

        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_memories()

    def load_memories(self):
        try:
            if not self.memory_file.exists():
                self.save_memories()
                return

            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.memories = data if isinstance(data, list) else []

            logger.info(f"Loaded {len(self.memories)} memories.")

        except Exception as e:
            logger.warning(f"Failed to load memories: {e}")
            self.memories = []

    def save_memories(self):
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.memories,
                    f,
                    indent=2,
                    ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    def add_memory(self, memory, memory_type="personal_fact"):
        memory = memory.strip()

        if not memory:
            return False

        # Don't save exact duplicates
        for item in self.memories:
            if item.get("memory", "").strip().lower() == memory.lower():
                return False

        self.memories.append({
            "memory": memory,
            "type": memory_type
        })

        self.save_memories()
        logger.info(f"Memory added: {memory}")

        return True

    def get_memories(self):
        return self.memories

    def clear_memories(self):
        self.memories = []
        self.save_memories()
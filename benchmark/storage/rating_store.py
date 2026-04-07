"""
人工评分存储
Rating Store - SQLite 存储
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


class RatingStore:
    """人工评分存储"""

    def __init__(self, db_path: str = "benchmark/ratings.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                rating_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                case_id TEXT,
                evaluator_id TEXT,
                ratings_json TEXT NOT NULL,
                overall_score REAL NOT NULL,
                feedback TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def save_rating(self, rating: Dict[str, Any]) -> None:
        """保存评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ratings
            (rating_id, task_id, case_id, evaluator_id, ratings_json, overall_score, feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rating["rating_id"],
            rating["task_id"],
            rating.get("case_id"),
            rating.get("evaluator_id"),
            json.dumps(rating["ratings"]),
            rating["overall_score"],
            rating.get("feedback", ""),
            rating.get("timestamp", datetime.utcnow().isoformat())
        ))
        conn.commit()
        conn.close()

    def get_task_ratings(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ratings WHERE task_id = ?", (task_id,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "rating_id": row[0],
                "task_id": row[1],
                "case_id": row[2],
                "evaluator_id": row[3],
                "ratings": json.loads(row[4]),
                "overall_score": row[5],
                "feedback": row[6],
                "created_at": row[7]
            }
            for row in rows
        ]

    def get_case_ratings(self, case_id: str) -> List[Dict[str, Any]]:
        """获取用例的所有评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ratings WHERE case_id = ?", (case_id,))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "rating_id": row[0],
                "task_id": row[1],
                "case_id": row[2],
                "evaluator_id": row[3],
                "ratings": json.loads(row[4]),
                "overall_score": row[5],
                "feedback": row[6],
                "created_at": row[7]
            }
            for row in rows
        ]

    def get_average_score(self, case_id: Optional[str] = None) -> float:
        """获取平均分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if case_id:
            cursor.execute("SELECT AVG(overall_score) FROM ratings WHERE case_id = ?", (case_id,))
        else:
            cursor.execute("SELECT AVG(overall_score) FROM ratings")

        avg = cursor.fetchone()[0]
        conn.close()

        return avg if avg else 0.0

    def get_all_ratings(self) -> List[Dict[str, Any]]:
        """获取所有评分"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ratings ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "rating_id": row[0],
                "task_id": row[1],
                "case_id": row[2],
                "evaluator_id": row[3],
                "ratings": json.loads(row[4]),
                "overall_score": row[5],
                "feedback": row[6],
                "created_at": row[7]
            }
            for row in rows
        ]

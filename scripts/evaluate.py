import asyncio
import json
import time
import argparse
from typing import List, Dict, Any
import aiosqlite

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph.workflow import app as graph_app
from src.core.logger import logger

class BenchmarkRunner:
    """Automated evaluation framework for Text-to-SQL performance."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.metrics = {
            "total_queries": 0,
            "success_count": 0,
            "failure_count": 0,
            "total_latency_sec": 0.0,
            "exact_match_accuracy": 0.0,
            "retries_triggered": 0,
            "errors": []
        }
        
    async def run_query_agent(self, question: str) -> Dict[str, Any]:
        """Runs a single query through the LangGraph agent and captures telemetry."""
        start_time = time.time()
        initial_state = {"question": question, "attempts": 0, "logs": []}
        
        final_state = None
        # Using the async generator to process the workflow
        async for event in graph_app.astream(initial_state, stream_mode="values"):
            final_state = event
            
        latency = time.time() - start_time
        
        return {
            "generated_sql": final_state.get("sql"),
            "results": final_state.get("results"),
            "error": final_state.get("error"),
            "attempts": final_state.get("attempts", 0),
            "latency": latency
        }
        
    async def evaluate_dataset(self, dataset: List[Dict[str, str]]):
        """Runs the benchmark across a subset of Spider or custom dataset."""
        logger.info(f"Starting benchmark on {len(dataset)} examples...")
        
        exact_matches = 0
        
        for item in dataset:
            self.metrics["total_queries"] += 1
            question = item["question"]
            expected_sql = item["query"]
            
            logger.info(f"Evaluating [{self.metrics['total_queries']}]: {question}")
            
            try:
                res = await self.run_query_agent(question)
                
                self.metrics["total_latency_sec"] += res["latency"]
                if res["attempts"] > 1:
                    self.metrics["retries_triggered"] += (res["attempts"] - 1)
                
                if res["error"]:
                    self.metrics["failure_count"] += 1
                    self.metrics["errors"].append({"question": question, "error": res["error"]})
                else:
                    self.metrics["success_count"] += 1
                    
                    # Exact execution match logic (run expected SQL and compare results)
                    if await self._compare_execution(res["generated_sql"], expected_sql):
                        exact_matches += 1
            except Exception as e:
                self.metrics["failure_count"] += 1
                self.metrics["errors"].append({"question": question, "error": str(e)})

        if self.metrics["success_count"] > 0:
            self.metrics["exact_match_accuracy"] = exact_matches / self.metrics["total_queries"]
            
        self._print_report()
        self._export_results()

    async def _compare_execution(self, generated_sql: str, expected_sql: str) -> bool:
        """Executes both queries on a read-only connection and compares the results."""
        if not generated_sql: return False
        try:
            async with aiosqlite.connect(f"file:{self.db_path}?mode=ro", uri=True) as db:
                async with db.execute(generated_sql) as cur1:
                    res1 = await cur1.fetchall()
                async with db.execute(expected_sql) as cur2:
                    res2 = await cur2.fetchall()
                # Compare sets of rows to ignore ordering differences unless ORDER BY is specified
                return set(res1) == set(res2)
        except Exception:
            return False

    def _print_report(self):
        print("\n" + "="*40)
        print("📊 BENCHMARK REPORT")
        print("="*40)
        print(f"Total Queries:         {self.metrics['total_queries']}")
        print(f"Success Rate:          {(self.metrics['success_count']/self.metrics['total_queries'])*100:.1f}%")
        print(f"Exact Match Accuracy:  {self.metrics['exact_match_accuracy']*100:.1f}%")
        print(f"Avg Latency:           {self.metrics['total_latency_sec']/self.metrics['total_queries']:.2f}s")
        print(f"Total Retries (Self-Correction): {self.metrics['retries_triggered']}")
        print("="*40)

    def _export_results(self, filename="benchmark_results.json"):
        with open(filename, "w") as f:
            json.dump(self.metrics, f, indent=4)
        logger.info(f"Results exported to {filename}")

if __name__ == "__main__":
    # Example minimal dataset representing Spider/WikiSQL format
    sample_dataset = [
        {"question": "How many tracks are there?", "query": "SELECT COUNT(*) FROM Track;"},
        {"question": "List all artists", "query": "SELECT Name FROM Artist;"},
        {"question": "Which artist has the most albums?", "query": "SELECT Artist.Name FROM Artist JOIN Album ON Artist.ArtistId = Album.ArtistId GROUP BY Artist.ArtistId ORDER BY COUNT(Album.AlbumId) DESC LIMIT 1;"}
    ]
    
    runner = BenchmarkRunner(db_path="Chinook_Sqlite.sqlite")
    asyncio.run(runner.evaluate_dataset(sample_dataset))

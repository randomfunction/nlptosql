import sys
import os
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.graph.workflow import app as graph_app

# Wrapper to mimic old interface
def process_question(query: str, details: bool = False):
    try:
        initial_state = {"question": query, "attempts": 0, "logs": []}
        final_state = graph_app.invoke(initial_state)
        
        # Check success based on error field or result presence
        if final_state.get("error"):
            return False, final_state.get("error")
            
        return True, final_state.get("final_answer")
    except Exception as e:
        return False, str(e)

TEST_CASES = [
    # 1. Simple / Baseline
    {"category": "Simple", "query": "How many tracks are there?"},
    {"category": "Simple", "query": "List all artist names."},
    
    # 2. Filtering
    {"category": "Filtering", "query": "Find all tracks that are longer than 5 minutes."},
    {"category": "Filtering", "query": "Which customers are from Brazil?"},
    
    # 3. Joins
    {"category": "Joins", "query": "List all tracks in the 'Rock' genre."},
    {"category": "Joins", "query": "Who is the artist for the album 'Machine Head'?"},
    
    # 4. Aggregation
    {"category": "Aggregation", "query": "What are the total sales for each country?"},
    {"category": "Aggregation", "query": "Which artist has the most albums?"},
    
    # 5. Complex Reasoning
    {"category": "Complex", "query": "List customers who have purchased both Rock and Jazz tracks."},
    {"category": "Complex", "query": "Which employee supports the customer with the highest total purchases?"},
    
    # 6. Edge Cases / Meta
    {"category": "Meta", "query": "What tables are in the database?"},
    {"category": "Ambiguity", "query": "Show me the best tracks."}, # Ambiguous
    {"category": "Negative", "query": "Find tracks with price greater than 100 dollars."} # Likely empty result
]

def run_tests():
    load_dotenv()
    print("🧪 Starting Test Suite...")
    print("=" * 50)
    
    results = {
        "Simple": {"pass": 0, "total": 0},
        "Filtering": {"pass": 0, "total": 0},
        "Joins": {"pass": 0, "total": 0},
        "Aggregation": {"pass": 0, "total": 0},
        "Complex": {"pass": 0, "total": 0},
        "Meta": {"pass": 0, "total": 0},
        "Ambiguity": {"pass": 0, "total": 0},
        "Negative": {"pass": 0, "total": 0},
    }
    
    for case in TEST_CASES:
        category = case["category"]
        query = case["query"]
        results[category]["total"] += 1
        
        print(f"\n[{category}] Query: {query}")
        try:
            # We assume process_question returns (success, result/message)
            success, result = process_question(query, details=False)
            
            if success:
                print("✅ PASSED")
                results[category]["pass"] += 1
            else:
                print(f"❌ FAILED: {result}")
        except Exception as e:
             print(f"❌ FAILED (Exception): {e}")

    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    for cat, stats in results.items():
        if stats["total"] > 0:
            rate = (stats["pass"] / stats["total"]) * 100
            print(f"{cat:<15} {stats['pass']}/{stats['total']} ({rate:.1f}%)")
        else:
            print(f"{cat:<15} 0/0 (N/A)")

if __name__ == "__main__":
    run_tests()

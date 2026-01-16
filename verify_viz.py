import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.graph.workflow import app as graph_app

def verify_viz():
    load_dotenv()
    print("🧪 Verifying Visualization...")
    query = "Total sales by country"
    state = {"question": query, "attempts": 0, "logs": []}
    
    final = graph_app.invoke(state)
    
    if final.get("visualization"):
        print("✅ Visualization Found!")
        print(final["visualization"])
    else:
        print("❌ Visualization Missing")
        print("Keys:", final.keys())

if __name__ == "__main__":
    verify_viz()

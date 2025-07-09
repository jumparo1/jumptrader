from flask import Flask, render_template, request, jsonify
import re
import json
from pathlib import Path
import sys
import os

# Add parent directory to path for mentorship module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mentorship.embed_store import ingest_transcript, query_store, get_store_stats, clear_store

app = Flask(__name__)

# In-memory lesson patterns and responses
LESSON_PATTERNS = {
    # Greetings
    "greeting": {
        "keywords": ["hi", "hello", "hey", "how are you", "what's up"],
        "response": "🔥 Hey trader! I'm Spicy, your AI mentor. I've learned from your lessons and I'm ready to help you level up your trading game. What's on your mind?"
    },
    
    # Trading bias logic (Lesson 4)
    "trade_today": {
        "keywords": ["trade today", "what to trade", "current bias", "market bias", "trading bias"],
        "response": "📊 **Current Trading Bias Logic:**\n\nBased on your lessons, here's how to determine your bias:\n\n1. **Check Market Context First:**\n   - Look for quiet environment (no coins ±10% on watchlist)\n   - Low FOMO signal - if you don't feel FOMO, others likely don't either\n   - Orion tick counts and volumes below recent averages\n\n2. **Duration of Regime Analysis:**\n   - Short-lived patterns (1hr): High upside potential but lower win-rate\n   - Long-lasting patterns (12hr+): Higher conviction, smaller moves but better risk management\n\n3. **Entry Triggers:**\n   - Perfect Support Tick (A++): Price touches support exactly, immediate reversal\n   - Swing Failure Pattern (SFP): Wick pierces level then closes back inside\n   - Clean Deviation & Return: Closes below support, then returns above\n\n4. **Trade Management:**\n   - Cut quickly on stair-step losses\n   - Hold through fast vertical spikes (normal reversion)\n   - Watch for outsized moves (>10-15%) - check news first\n\n🔥 **Spicy's Take:** Context is everything. Always check market conditions before applying any strategy!"
    },
    
    # Mean reversion strategies (Lesson 1)
    "mean_reversion": {
        "keywords": ["mean reversion", "reversion", "support", "bounce", "pullback"],
        "response": "🔄 **Mean Reversion Strategies:**\n\n**Perfect Entry Triggers:**\n• **Perfect Support Tick (A++):** Price touches support exactly, next candle immediately reverses up\n• **Swing Failure Pattern (SFP):** Wick pierces level then closes back inside\n• **Clean Deviation & Return:** Closes below support, then returns above quickly\n\n**Market Context Requirements:**\n• Quiet environment - no coins ±10% on watchlist\n• Low FOMO signal\n• Orion tick counts below recent averages\n• Balanced spot return buckets\n\n**Trade Management:**\n• Cut quickly on stair-step losses\n• Hold through fast vertical spikes\n• Watch for outsized moves (>10-15%)"
    },
    
    # Duration and regime analysis (Lesson 2)
    "duration_regime": {
        "keywords": ["duration", "regime", "pattern", "how long", "persist"],
        "response": "⏰ **Duration of Regime Analysis:**\n\n**Key Concept:** How long a market pattern (trend or chop) has persisted.\n\n**Short-lived Patterns (1hr):**\n• High upside potential but low conviction\n• Lower win-rate, bigger potential moves\n• Early in the cycle\n\n**Long-lasting Patterns (12hr+):**\n• High conviction for momentum trades\n• Smaller moves but higher win-rate\n• Easier risk management\n\n**Trade-off:**\n• Early regime → big wins possible, more losers\n• Established regime → smaller moves, higher win-rate\n\n**Press-Start Analogy:**\n• Early press: High variance, step on gas for big P&L swings\n• Late press: Lower variance, focus on consistent smaller gains"
    },
    
    # Levels and support/resistance (Lesson 3)
    "levels": {
        "keywords": ["levels", "support", "resistance", "limit orders", "time spent"],
        "response": "📈 **Levels & Support/Resistance:**\n\n**What is a Level?**\n• Support = area with many limit buy orders\n• Resistance = area with many limit sell orders\n• No 'good' vs 'bad' levels by geometry - only by USD size of resting orders\n\n**Why Time Matters:**\n• Time spent away from a level is key to picking high-quality levels\n• This drives trade management and average win-to-loss ratios\n• Levels with more time away tend to be stronger\n\n**Level Selection:**\n• For reversion: all swing lows except those with large 'empty space' beyond\n• For momentum: only levels with empty space on the opposite side"
    },
    
    # Session preparation (Lesson 5)
    "session_prep": {
        "keywords": ["session", "preparation", "prep", "before trading", "setup"],
        "response": "🎯 **Session Preparation:**\n\n**Pre-Session Checklist:**\n• Review market context and regime duration\n• Check Orion tick counts and volume patterns\n• Identify key support/resistance levels\n• Set up watchlist with potential setups\n\n**Market Context Review:**\n• Check if environment is quiet (no ±10% moves)\n• Verify low FOMO conditions\n• Review recent volume and tick patterns\n\n**Level Preparation:**\n• Mark key support/resistance levels\n• Note levels with 'empty space' beyond\n• Identify potential entry triggers\n\n**Mental Preparation:**\n• Decide on bias (momentum vs reversion)\n• Set risk parameters\n• Prepare for both scenarios"
    },
    
    # Top tick analysis (Lesson 6)
    "top_tick": {
        "keywords": ["top tick", "tick", "orion", "volume", "tick count"],
        "response": "📊 **Top Tick Analysis:**\n\n**Orion Tick Count & Volume:**\n• Look for tick counts and volumes below recent averages\n• Harder to find coins meeting volume criteria → ideal for reversion\n• No fixed 'low' threshold - use discretion against recent 4-6 day history\n\n**Relative Filters:**\n• If BTC ticks >100k in 5 min → consider momentum in BTC, not alts\n• Use comparative history rather than absolute numbers\n\n**Velo / Other Data:**\n• Spot return buckets should be balanced, not skewed\n• Low spot volume on big movers flags 'false pumps'\n\n**Context Integration:**\n• Combine with market environment analysis\n• Use as confirmation for entry triggers\n• Monitor for regime changes"
    },
    
    # Risk management (across lessons)
    "risk_management": {
        "keywords": ["risk", "management", "cut", "hold", "exit", "stop loss"],
        "response": "⚠️ **Risk Management Principles:**\n\n**When to Cut Quickly:**\n• Price grinds against you in a staircase fashion\n• New market condition emerges (e.g., Bitcoin spikes in sync with alt)\n• Stair-step losses indicate trend continuation\n\n**When to Hold Through:**\n• Fast vertical spike against you (normal reversion pullback)\n• Choppiness at entry in slow, boring environment\n• Swift spikes often reverse quickly\n\n**Position Management:**\n• Cut on stair-step losses\n• Hold on swift spikes\n• Watch for outsized moves (>10-15%) - check news first\n\n**Context Matters:**\n• Market regime affects risk tolerance\n• Duration of pattern influences exit timing\n• Always consider overall market conditions"
    }
}

def load_lessons():
    """Load lessons from sample_transcript.txt into memory"""
    try:
        transcript_path = Path(__file__).parent.parent / "sample_transcript.txt"
        if transcript_path.exists():
            with open(transcript_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ingest into the embed store
            if get_store_stats()["total_documents"] == 0:
                ingest_transcript(content, "sample_lessons")
                print("✅ Loaded lessons into Spicy's memory")
            else:
                print("✅ Lessons already loaded in Spicy's memory")
        else:
            print("⚠️ No sample_transcript.txt found")
    except Exception as e:
        print(f"❌ Error loading lessons: {e}")

def find_matching_pattern(user_message):
    """Find the best matching pattern for the user's message"""
    user_message_lower = user_message.lower()
    
    # Check each pattern
    for pattern_name, pattern_data in LESSON_PATTERNS.items():
        for keyword in pattern_data["keywords"]:
            if keyword in user_message_lower:
                return pattern_data["response"]
    
    # If no pattern matches, try semantic search
    try:
        excerpts = query_store(user_message, k=2)
        if excerpts:
            response = "🤔 **Based on your lessons:**\n\n"
            for i, excerpt in enumerate(excerpts, 1):
                clean_excerpt = excerpt.replace('\n', ' ').strip()
                response += f"**{i}.** {clean_excerpt[:200]}...\n\n"
            response += "\n🔥 **Spicy's Take:** This is what I found in your lessons. Need more specific info?"
            return response
    except Exception as e:
        print(f"Error in semantic search: {e}")
    
    return "🤔 Sorry, I don't have that yet—upload more lessons! 🔥"

@app.route('/')
def index():
    """Serve the main chat interface"""
    return render_template('index.html')

@app.route('/api/message', methods=['POST'])
def handle_message():
    """Handle incoming chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'answer': 'Please type a message!'})
        
        # Get Spicy's response
        reply = find_matching_pattern(user_message)
        
        return jsonify({'answer': reply})
    
    except Exception as e:
        print(f"Error handling message: {e}")
        return jsonify({'answer': '🔥 Oops! Something went wrong. Try again!'})

@app.route('/api/status')
def status():
    """Return Spicy's status"""
    stats = get_store_stats()
    return jsonify({
        'lessons_loaded': stats['total_documents'],
        'knowledge_chunks': stats['total_chunks'],
        'status': 'ready' if stats['total_documents'] > 0 else 'needs_lessons'
    })

if __name__ == '__main__':
    # Load lessons on startup
    load_lessons()
    
    print("🔥 Spicy is starting up...")
    print("📚 Lessons loaded and ready!")
    print("🌐 Server starting on http://localhost:5000")
    
    app.run(debug=True, host='localhost', port=5000) 
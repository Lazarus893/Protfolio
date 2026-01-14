import os
import json
import anthropic
import time
from datetime import datetime
from config import ANTHROPIC_API_KEY

# Configuration
CLAUDE_API_KEY = ANTHROPIC_API_KEY

ANALYSIS_PROMPT_TEMPLATE = """
Analyze the following session content. Return ONLY a valid JSON object. Do not include any explanation or markdown formatting outside the JSON.

SESSION CONTENT:
{session_content}

---

## TASK: 3-Part Analysis

### Part 1: Data Source Nodes
Identify `makeXxxNode` factory functions in the code.
- Ignore helper functions.
- Extract params, output schema, and usage context.

### Part 2: User Query Analysis
Evaluate the User's question:
- Topic: Classify into stock trading categories (e.g., FUNDAMENTAL_ANALYSIS, TECHNICAL_ANALYSIS).
- Sentiment: POSITIVE, NEGATIVE, or NEUTRAL.
- Strategy Potential: Is this a valuable trading strategy idea? Why? (Confidence: HIGH/MEDIUM/LOW). **IMPORTANT: Write the reasoning in Chinese (中文).**

### Part 3: Response Evaluation
Evaluate the Model's answer:
- Score: 1-5 overall quality.
- Risk: Hallucination risk (LOW/MEDIUM/HIGH).
- Quality Metrics: Accuracy, Clarity, Completeness.

## REQUIRED JSON OUTPUT FORMAT

```json
{{
  "nodes": [
    {{
      "name": "makeXxxNode",
      "purpose": "string",
      "output_key": "string",
      "params": ["param1", "param2"]
    }}
  ],
  "query_analysis": {{
    "topic": "string",
    "sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
    "strategy_potential": {{
      "is_valuable": boolean,
      "reasoning": "string",
      "confidence": "HIGH|MEDIUM|LOW"
    }}
  }},
  "response_evaluation": {{
    "overall_score": number,
    "risk_level": "LOW|MEDIUM|HIGH",
    "quality_metrics": {{
      "accuracy": number,
      "clarity": number,
      "completeness": number
    }}
  }},
  "summary": "string - 1 sentence summary of the interaction"
}}
```
"""

def analyze_session(session_data):
    """
    Analyze the session content using Claude API (via Official SDK).
    """
    
    # Format session content for the prompt
    dialogs = session_data.get('dialogs', {}).get('list', [])
    if not dialogs:
        return {"error": "No dialogs found in session"}
        
    formatted_content = ""
    for dialog in dialogs:
        formatted_content += f"User Query:\n{dialog.get('question', '')}\n\n"
        formatted_content += f"Model Output:\n{dialog.get('answer', '')}\n\n"
        formatted_content += "-" * 40 + "\n\n"
        
    timestamp = datetime.now().isoformat()
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        session_content=formatted_content,
        timestamp=timestamp
    )
    
    if not CLAUDE_API_KEY:
        return {"error": "Anthropic API key is not configured"}

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    
    max_retries = 3
    retry_delay = 2 # seconds
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            print(f"Sending analysis request (Attempt {attempt+1})...")
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            print(f"Raw Model Response:\n{content[:500]}...") # Log first 500 chars
            
            # Robust JSON extraction
            # 1. Try finding the first { and last }
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"error": "Failed to parse JSON from model response", "raw_content": content}
                
        except Exception as e:
            last_exception = e
            print(f"Analysis attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
            
    return {"error": f"Analysis failed after {max_retries} attempts: {str(last_exception)}"}

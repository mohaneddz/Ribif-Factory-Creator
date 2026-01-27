"""
General utility functions
"""

import json
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env file
load_dotenv()


def ask_llm(prompt: str, system_prompt: str = None, temperature: float = 0.7, max_tokens: int = 8000) -> str:
    """
    Send a prompt to Groq's Gemini Flash model and get a response.
    
    Args:
        prompt: The user prompt to send to the LLM
        system_prompt: Optional system prompt to guide the LLM's behavior
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens in the response
        
    Returns:
        The LLM's response as a string
    """
    # Get API key from environment
    API_KEY = os.getenv("GROQ_API_KEY")
    if not API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables")
    
    # Initialize Groq client
    client = Groq(api_key=API_KEY)
    
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })
    messages.append({
        "role": "user",
        "content": prompt
    })
    
    # Make API call
    try:
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",  # Groq's Llama 3.3 70B model
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return chat_completion.choices[0].message.content
    
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        raise


def ask_llm_json(prompt: str, system_prompt: str = None, temperature: float = 0.7) -> dict:
    """
    Send a prompt to the LLM and parse the response as JSON.
    
    Args:
        prompt: The user prompt to send to the LLM
        system_prompt: Optional system prompt to guide the LLM's behavior
        temperature: Sampling temperature (0.0-2.0)
        
    Returns:
        The LLM's response parsed as a dictionary
    """
    response = ask_llm(prompt, system_prompt, temperature)
    
    # Try to extract JSON from markdown code blocks if present
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()
    
    return json.loads(response)
"""
LLM Reasoner Module
Loads TinyLlama-1.1B-Chat once at startup and generates answers
"""
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Global variables to store model and tokenizer
model = None
tokenizer = None
device = None

def load_model():
    """Load TinyLlama model once at startup"""
    global model, tokenizer, device
    
    print("\n" + "="*60)
    print("Loading TinyLlama-1.1B-Chat-v1.0...")
    print("="*60)
    
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    
    try:
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        
        # Load tokenizer
        print("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        # Set padding token to eos token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model (no quantization for Windows compatibility)
        print("Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,  # Use float32 for CPU
            low_cpu_mem_usage=True
        )
        
        # Move to device and set to eval mode
        model.to(device)
        model.eval()
        
        print("✓ Model loaded successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        print("Continuing without LLM support...")
        model = None
        tokenizer = None

def generate_answer(prompt, max_new_tokens=400, temperature=0.7):
    """
    Generate answer from prompt using TinyLlama
    
    Args:
        prompt: Context + question prompt
        max_new_tokens: Maximum tokens to generate (increased to 400 for complete answers)
        temperature: Sampling temperature (0.7 = balanced)
    
    Returns:
        Generated answer string
    """
    global model, tokenizer, device
    
    if model is None or tokenizer is None:
        return "LLM not available. Please check model loading."
    
    try:
        # Format prompt for chat model - emphasize English language
        chat_prompt = f"<|system|>\nYou are a helpful story analysis assistant who provides detailed, accurate answers in English. Always respond in English language only, never in Hindi, Japanese, Chinese, or any other language.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        
        # Tokenize with attention_mask
        inputs = tokenizer(
            chat_prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=2048,
            padding=True,
            return_attention_mask=True
        )
        inputs = inputs.to(device)
        
        print(f"⚙️  Generating answer (this may take 1-5 minutes on CPU)...")
        print(f"⚙️  Processing {inputs.input_ids.shape[1]} input tokens...")
        
        import time
        start_time = time.time()
        
        # Generate with attention mask
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,  # Reduce repetition
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        elapsed = time.time() - start_time
        
        # Decode only the new tokens
        generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        
        tokens_generated = outputs[0].shape[0] - inputs.input_ids.shape[1]
        print(f"✓ Generated {tokens_generated} tokens in {elapsed:.1f}s ({tokens_generated/elapsed:.1f} tokens/sec)")
        
        return generated_text.strip()
        
    except Exception as e:
        print(f"✗ Error generating answer: {e}")
        import traceback
        traceback.print_exc()
        return "I encountered an error generating the answer. Please try again."

def initialize_model():
    """Public function to initialize model (called at startup)"""
    load_model()
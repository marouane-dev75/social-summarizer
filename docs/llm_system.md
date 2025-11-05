# LLM System Documentation

The Time Reclamation App includes a comprehensive LLM (Large Language Model) system that allows you to interact with local language models for various one-shot tasks. This system follows the same architectural patterns as the notification system, providing a consistent and extensible interface.

## Overview

The LLM system supports:
- **Multiple LLM Instances**: Configure different models for different purposes
- **Local Model Support**: Uses llama-cpp-python for local GGUF models
- **Cloud API Support**: Integrates with Anthropic Claude and OpenAI GPT models
- **One-Shot Tasks**: Designed for single prompt-response interactions
- **Flexible Configuration**: Easy setup through config.yml
- **CLI Interface**: Simple command-line interface for generating responses
- **Resource Management**: Efficient model loading and cleanup

## Architecture

The LLM system follows a modular architecture:

```
src/time_reclamation/infrastructure/llm/
├── __init__.py              # Module exports
├── interface.py             # Abstract LLM provider interface
├── manager.py              # LLM manager for multiple instances
└── providers/
    ├── __init__.py         # Provider exports
    ├── llamacpp.py         # LlamaCpp provider implementation
    ├── anthropic.py        # Anthropic Claude provider implementation
    └── openai.py           # OpenAI GPT provider implementation
```

### Core Components

1. **LLMProvider Interface**: Abstract base class defining the contract for all LLM providers
2. **LLMManager**: High-level manager handling multiple provider instances
3. **LlamaCppProvider**: Implementation for local GGUF models using llama-cpp-python
4. **AnthropicProvider**: Implementation for Anthropic Claude models via API
5. **OpenAIProvider**: Implementation for OpenAI GPT models via API
6. **LLMCommand**: CLI command for interacting with the LLM system

## Configuration

### Basic Setup

Add LLM configuration to your `config.yml`:

```yaml
llm:
  providers:
    - name: "general_assistant"
      type: "llamacpp"
      enabled: true
      config:
        model_path: "/path/to/your/model.gguf"
        context_size: 4096
        gpu_layers: 33
        generation_config:
          max_tokens: 8000
          temperature: 0.7
          top_p: 0.9
          top_k: 40
          repeat_penalty: 1.1
        default_system_prompt: "You are a helpful AI assistant."

    # Anthropic Claude Configuration
    - name: "claude_assistant"
      type: "anthropic"
      enabled: true
      config:
        api_key: "your-anthropic-api-key-here"
        model: "claude-haiku-4.5"
        max_tokens: 4000
        temperature: 0.7
        default_system_prompt: "You are Claude, a helpful AI assistant created by Anthropic."

    # OpenAI GPT Configuration
    - name: "gpt_assistant"
      type: "openai"
      enabled: true
      config:
        api_key: "your-openai-api-key-here"
        model: "gpt-5"
        max_tokens: 4000
        temperature: 0.7
        default_system_prompt: "You are a helpful AI assistant."
```

### Configuration Parameters

#### Model Configuration
- `model_path`: Path to your GGUF model file (required)
- `context_size`: Context window size (default: 4096)
- `gpu_layers`: Number of layers to offload to GPU (0 = CPU only, -1 = all layers)

#### Generation Parameters
- `max_tokens`: Maximum tokens to generate
- `temperature`: Creativity level (0.0 = deterministic, 1.0 = very creative)
- `top_p`: Nucleus sampling parameter
- `top_k`: Top-k sampling parameter
- `repeat_penalty`: Penalty for repetition
- `stop`: Stop sequences (optional)

#### Anthropic Configuration Parameters
- `api_key`: Your Anthropic API key (required)
- `model`: Claude model to use (e.g., "claude-haiku-4.5", "claude-sonnet-4.5", "claude-opus-4.1")
- `max_tokens`: Maximum tokens to generate
- `temperature`: Creativity level (0.0 = deterministic, 1.0 = very creative)

#### OpenAI Configuration Parameters
- `api_key`: Your OpenAI API key (required)
- `model`: GPT model to use (e.g., "gpt-5", "o3", "o4-mini")
- `max_tokens`: Maximum tokens to generate
- `temperature`: Creativity level (0.0 = deterministic, 2.0 = very creative)

#### System Prompt
- `default_system_prompt`: Default system prompt for the instance
- `chat_template`: Custom chat template (optional, LlamaCpp only)

### Multiple Instances Example

```yaml
llm:
  providers:
    - name: "general_assistant"
      type: "llamacpp"
      enabled: true
      config:
        model_path: "/models/llama-2-7b-chat.Q4_K_M.gguf"
        context_size: 4096
        gpu_layers: 33
        generation_config:
          max_tokens: 8000
          temperature: 0.7
        default_system_prompt: "You are a helpful AI assistant."
    
    - name: "code_expert"
      type: "llamacpp"
      enabled: true
      config:
        model_path: "/models/codellama-7b.Q4_K_M.gguf"
        context_size: 8192
        gpu_layers: 0  # CPU only
        generation_config:
          max_tokens: 4000
          temperature: 0.3  # Lower temperature for code
        default_system_prompt: "You are an expert programmer."
```

## Getting Started

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `llama-cpp-python>=0.2.0` along with other dependencies.

### 2. Download a Model

Download a GGUF model from Hugging Face. Popular options:

```bash
# Create models directory
mkdir models
cd models

# Llama 2 7B Chat (4-bit quantized, ~3.8GB)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf

# Code Llama 7B (4-bit quantized, ~3.8GB)
wget https://huggingface.co/TheBloke/CodeLlama-7B-GGUF/resolve/main/codellama-7b.Q4_K_M.gguf

# Mistral 7B Instruct (4-bit quantized, ~4.1GB)
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF/resolve/main/mistral-7b-instruct-v0.1.Q4_K_M.gguf
```

### 3. Configure Your Instance

Update `config.yml` with your model path:

```yaml
llm:
  providers:
    - name: "my_assistant"
      type: "llamacpp"
      enabled: true
      config:
        model_path: "./models/llama-2-7b-chat.Q4_K_M.gguf"
        # ... other configuration
```

### 4. Test Your Setup

```bash
# List available instances
python main.py llm --list

# Test connections
python main.py llm --test

# Generate a response
python main.py llm --prompt "Hello, how are you?"
```

## CLI Usage

### Basic Commands

```bash
# Show available LLM instances
python main.py llm --list

# Test all instances
python main.py llm --test

# Test specific instance
python main.py llm --test my_assistant

# Generate response with auto-selected instance
python main.py llm --prompt "Explain quantum computing"

# Use specific instance
python main.py llm my_assistant --prompt "Write a Python function"

# Use custom system prompt
python main.py llm --system "You are a poet" --prompt "Write a haiku about coding"
```

### Command Aliases

You can use these aliases for the `llm` command:
- `ai`: `python main.py ai --prompt "Your question"`
- `generate`: `python main.py generate --prompt "Your request"`

### Advanced Usage

```bash
# Complex prompt with specific instance and system prompt
python main.py llm code_expert \
  --system "You are a Python expert. Provide clean, documented code." \
  --prompt "Create a function to calculate fibonacci numbers with memoization"

# Using module syntax
python -m time_reclamation llm --prompt "What is machine learning?"
```

## Programming Interface

### Basic Usage

```python
from src.time_reclamation.infrastructure.llm import get_llm_manager, generate_llm_response

# Simple generation
result = generate_llm_response("What is the capital of France?")
if result.status == LLMStatus.SUCCESS:
    print(result.response)

# With specific instance and system prompt
result = generate_llm_response(
    user_prompt="Write a Python function to sort a list",
    instance_name="code_expert",
    system_prompt="You are a Python expert"
)
```

### Advanced Usage

```python
from src.time_reclamation.infrastructure.llm import get_llm_manager, LLMStatus

# Get manager instance
llm_manager = get_llm_manager()

# Check available instances
instances = llm_manager.get_available_instances()
print(f"Available instances: {instances}")

# Generate with custom parameters
result = llm_manager.generate_response(
    user_prompt="Explain neural networks",
    instance_name="general_assistant",
    system_prompt="You are a teacher. Explain concepts simply.",
    temperature=0.5,
    max_tokens=1000
)

# Handle the result
if result.status == LLMStatus.SUCCESS:
    print(f"Response: {result.response}")
    print(f"Generation time: {result.generation_time:.2f}s")
else:
    print(f"Error: {result.error_details}")

# Test providers
test_results = llm_manager.test_providers()
for instance_name, result in test_results.items():
    status = "✓" if result.status == LLMStatus.SUCCESS else "✗"
    print(f"{status} {instance_name}: {result.response or result.error_details}")

# Cleanup when done
llm_manager.cleanup_all()
```

## Model Recommendations

### General Purpose Models

1. **Llama 2 7B Chat** (Recommended for beginners)
   - Size: ~3.8GB (Q4_K_M quantization)
   - Good balance of quality and speed
   - Well-suited for general conversations

2. **Mistral 7B Instruct**
   - Size: ~4.1GB (Q4_K_M quantization)
   - Excellent instruction following
   - Good for various tasks

### Specialized Models

1. **Code Llama 7B** (For programming tasks)
   - Size: ~3.8GB (Q4_K_M quantization)
   - Specialized for code generation
   - Supports multiple programming languages

2. **Phi-3 Mini** (For resource-constrained environments)
   - Size: ~2.2GB (Q4 quantization)
   - Smaller but still capable
   - Faster inference

### Performance Considerations

- **GPU vs CPU**: Use `gpu_layers` to control GPU usage
- **Context Size**: Larger context uses more memory
- **Quantization**: Q4_K_M offers good quality/size balance
- **Temperature**: Lower for focused tasks, higher for creativity

## Troubleshooting

### Common Issues

#### Model Not Found
```
Error: Model file not found at /path/to/model.gguf
```
**Solution**: Verify the model path in your config.yml and ensure the file exists.

#### Import Error
```
Error: llama-cpp-python is not installed
```
**Solution**: Install the dependency:
```bash
pip install llama-cpp-python>=0.2.0
```

#### GPU Issues
```
Error initializing model: CUDA out of memory
```
**Solutions**:
- Reduce `gpu_layers` or set to 0 for CPU-only
- Use a smaller model or lower quantization
- Reduce `context_size`

#### Slow Performance
**Solutions**:
- Increase `gpu_layers` if you have GPU
- Use a smaller model
- Reduce `context_size`
- Use higher quantization (Q4 instead of Q8)

### Configuration Validation

The system validates configuration automatically:
- Checks if model files exist
- Validates GGUF file format
- Tests model loading during initialization

### Logging

Enable debug logging to troubleshoot issues:

```bash
python main.py llm --prompt "test" --debug
```

Or in code:
```python
from src.time_reclamation.infrastructure import get_logger
logger = get_logger()
logger.set_level("DEBUG")
```

## Best Practices

### Configuration
- Use descriptive instance names
- Set appropriate `gpu_layers` for your hardware
- Configure different instances for different use cases
- Use lower temperature for factual tasks, higher for creative tasks

### Usage
- Test your configuration before production use
- Clean up resources when done (automatic in CLI)
- Use specific instances for specialized tasks
- Provide clear system prompts for better results

### Performance
- Load models once and reuse (handled automatically)
- Use appropriate quantization levels
- Monitor memory usage with large models
- Consider model size vs. quality trade-offs

## Extending the System

### Adding New Providers

To add support for other LLM providers (OpenAI, Anthropic, etc.):

1. Create a new provider class implementing `LLMProvider`
2. Add it to the providers module
3. Update the manager to handle the new provider type
4. Add configuration examples

Example structure:
```python
class OpenAIProvider(LLMProvider):
    def generate(self, system_prompt: str, user_prompt: str, **kwargs) -> LLMResult:
        # Implementation here
        pass
    
    # ... other required methods
```

### Custom Chat Templates

You can customize the chat template for different model formats:

```yaml
config:
  chat_template: |
    ### System:
    {system_prompt}
    
    ### User:
    {user_prompt}
    
    ### Assistant:
```

## Integration Examples

### With Notification System

```python
from src.time_reclamation.infrastructure.llm import generate_llm_response
from src.time_reclamation.infrastructure.notifications import send_notification

# Generate a summary
result = generate_llm_response(
    "Summarize today's important events",
    system_prompt="You are a news summarizer"
)

if result.status == LLMStatus.SUCCESS:
    # Send summary via notification
    send_notification(f"Daily Summary:\n{result.response}")
```

### Batch Processing

```python
prompts = [
    "Explain machine learning",
    "What is quantum computing?",
    "How does blockchain work?"
]

for prompt in prompts:
    result = generate_llm_response(prompt)
    if result.status == LLMStatus.SUCCESS:
        print(f"Q: {prompt}")
        print(f"A: {result.response}\n")
```

This documentation provides a comprehensive guide to using the LLM system in the Time Reclamation App. The system is designed to be flexible, extensible, and easy to use while following established architectural patterns.